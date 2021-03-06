import logging
import os
import threading
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework import mixins
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from django.conf import settings

from apps.host import serializer
from apps.host.models import HostModel, Cluster
from apps.accounts.authentication import Authentication
from apps.task.views import script_task
from lib import *
from lib.exception import APIException
from lib.excel import Excel
from lib.validates import validate_ssh
from concurrent.futures import ThreadPoolExecutor, as_completed
from apps.alarm.views import _create_alarm_message


logger = logging.getLogger(__name__)


class HostModelViewSet(GenericViewSet,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.CreateModelMixin,
                       mixins.DestroyModelMixin
                       ):
    queryset = HostModel.objects.filter(deleted_at=None)
    serializer_class = serializer.HostListSerializer
    authentication_classes = [Authentication]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ip', 'hostname', 'cluster', 'status']

    def get_authenticators(self):
        if self.request.method == "GET":
            return []
        else:
            return [auth() for auth in self.authentication_classes]

    def create(self, request, *args, **kwargs):
        context = request.data
        self._thread_pool(tasks=[context], func=self._validate_and_initialize_host)
        return success(result={})

    def _validate_and_initialize_host(self, context):
        context = validate_ssh(context)
        create_serializer = self.get_serializer(data=context)
        create_serializer.is_valid(raise_exception=True)
        self.perform_create(create_serializer)
        instance = create_serializer.instance
        # ????????????client???????????? ??????host??????
        thread = threading.Thread(
            target=self.client_deploy_cmd_init, args=(instance,))
        thread.start()
        ser = serializer.HostListSerializer(instance=instance)
        return ser

    def perform_create(self, ser):
        ser.save(created_by=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.check_instance_exist(request, *args, **kwargs)
        if not instance:
            return not_found()
        ser = self.get_serializer(instance)
        return success(result=ser.data)

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializer.HostListSerializer
        else:
            return serializer.AddHostSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if not queryset:
            return success([], total=0)
        return super(HostModelViewSet, self).list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.check_instance_exist(request, *args, **kwargs)
        if not instance:
            return not_found()
        status, content = self.client_deploy_cmd_delete(instance)
        if status != 200:
            return other_response(message="?????????????????????????????????????????????????????????{}".format(content.get("message")), code=400, success=False)
        self.perform_destroy(instance)
        return success(message="????????????", code=200, result={})

    def perform_destroy(self, instance: HostModel):
        instance.deleted_at = human_datetime()
        instance.deleted_by = self.request.user
        instance.save()

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return success(result=response.data, message="????????????")

    def check_instance_exist(self, request, *args, **kwargs):
        instance = self.get_queryset().filter(**kwargs).first()
        return instance if instance else None

    def client_deploy_cmd_init(self, instance):
        data = {"service_name": "node_init",
                "instance": instance.ip,
                "update_host_status": True
                }
        script_task(data)

    def client_deploy_cmd_delete(self, instance):
        try:
            data = {"service_name": "node_delete",
                    "instance": instance.ip
                    }
            resp = script_task(data)
            logger.info(resp.status_code, resp.data)
            return resp.status_code, resp.data
        except Exception as e:
            logger.error(e, exc_info=True)
            return False, str(e)

    def _get_cluster_instance(self, cluster_name):
        try:
            instance = Cluster.objects.get(cluster_name=cluster_name)
            return instance
        except Cluster.DoesNotExist:
            return None

    def _thread_pool(self, tasks: list, func):
        kwargs = {}
        kwargs['sub'] = 1
        kwargs['item'] = 'host'
        pool = []
        workers = len(tasks) if len(tasks) < os.cpu_count() else os.cpu_count() * 2

        with ThreadPoolExecutor(max_workers=workers) as p:
            for task in tasks:
                t = p.submit(func, task)
                pool.append(t)

            for d in as_completed(pool):
                try:
                    response = d.result()
                    kwargs['message'] = f"IP: {response.data.get('ip')} ????????????!"
                    kwargs['collected_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    kwargs['level'] = 3
                    _create_alarm_message(kwargs)

                except ValidationError as e:
                    kwargs['message'] = ','.join(
                        [f'{k}: {v[0]}' for k, v in e.detail.items()])
                    kwargs['collected_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    kwargs['level'] = 2
                    _create_alarm_message(kwargs)
                except Exception as e:
                    kwargs['message'] = e.message
                    kwargs['level'] = 2
                    kwargs['collected_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    _create_alarm_message(kwargs)

    def batch_add_host(self, request: Request):
        file = request.FILES.get('file', None)
        if not file:
            return other_response(message='Excel File Required!', code=400, success=False)
        e = Excel(file.read())
        tasks = []

        kwargs = {
            "item": "host",
            "sub": 1
        }
        for row in e.values():
            cluster = self._get_cluster_instance(row['cluster'])
            if not cluster:
                kwargs.update({'level': 2})
                kwargs.update({'message': f"The cluster field {row['cluster']} of host {row['ip']} does not exist!"})
                kwargs.update({'collected_time': human_datetime()})
                _create_alarm_message(kwargs)
                continue
            row['cluster'] = cluster.id
            tasks.append(row)

        self._thread_pool(tasks=tasks, func=self._validate_and_initialize_host)
        return success(result={})


class ClusterViewSet(GenericViewSet,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin,
                     mixins.CreateModelMixin,
                     mixins.UpdateModelMixin):
    queryset = Cluster.objects.filter(Q(deleted_at=None) | Q(deleted_at=""))
    serializer_class = serializer.ClusterListSerializer

    def get_authenticators(self):
        if self.request.method == "GET":
            return []
        else:
            return [auth() for auth in self.authentication_classes]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializer.ClusterListSerializer
        else:
            return serializer.AddClusterSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if not queryset:
            return success([], total=0)
        return super(ClusterViewSet, self).list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return success(result=response.data)

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return success(result={}, message="????????????")

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return success(result={}, message="????????????")


class SaveUploadFile(APIView):
    authentication_classes = []

    @swagger_auto_schema(operation_description="????????????",
                         request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             required=["file"],
                             properties={
                                 "file": openapi.Schema(type=openapi.TYPE_FILE),
                                 "catalogue": openapi.Schema(type=openapi.TYPE_STRING)

                             }
                         ),
                         responses={
                             '200': openapi.Response('save upload success', examples={"application/json": {
                                 "code": 200,
                                 "message": "Upload success",
                                 "data": {}
                             }}),
                             '400': openapi.Response('Fail', examples={"application/json": {
                                 "code": 400,
                                 "message": "Required Field: file",
                                 "data": {}
                             }})
                         }
                         )
    def post(self, request):
        file = request.data.get('file', None)
        catalogue = request.data.get('catalogue', None)
        if not file:
            return APIException(message="Upload Failed: file required!")

        file_path = os.path.join(
            settings.MEDIA_ROOT, catalogue) if catalogue else settings.MEDIA_ROOT
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        path = os.path.join(file_path, file.name)
        try:
            with open(path, 'wb') as f:
                for chunk in file.chunks():
                    f.write(chunk)
        except Exception as e:
            logger.error(e)
            raise APIException(message=f"Upload Failed: {e}")
        return success(result={}, message="Upload success")
