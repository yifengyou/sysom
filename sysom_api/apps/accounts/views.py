from datetime import datetime
import logging
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet
from rest_framework import mixins, status
from rest_framework.status import *
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView

from apps.accounts.permissions import IsAdminPermission
from apps.accounts.serializer import UserAuthSerializer
from apps.accounts.authentication import Authentication

from . import models
from . import serializer
from lib import success, other_response

logger = logging.getLogger(__name__)


class UserModelViewSet(
    GenericViewSet,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.RetrieveModelMixin
):
    queryset = models.User.objects.all()
    serializer_class = serializer.UserListSerializer
    # permission_classes = [IsAdminPermission]
    logging_options = {
        'login': 0,
        'action': 1
    }

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializer.UserListSerializer
        else:
            return serializer.AddUserSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        else:
            return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return success(result=response.data, message="εε»Ίζε")

    def list(self, request, *args, **kwargs):
        data = super().list(request, *args, **kwargs)
        return success(result=data.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        u_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        u_serializer.is_valid(raise_exception=True)
        self.perform_update(u_serializer)

        result = serializer.UserListSerializer(instance=u_serializer.instance, many=False)
        return success(result=result.data, message="δΏ?ζΉζε")

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return success(result={}, message="ε ι€ζε")

    def retrieve(self, request, *args, **kwargs):
        result = super().retrieve(request, *args, **kwargs)
        return success(result=result.data, message="θ·εζε")

    def get_logs(self, request):
        queryset = self._filter_log_params(request, models.HandlerLog.objects.select_related().all())
        user = getattr(request, 'user', None)
        if not user.is_admin:
            queryset = queryset.filter(user=user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            ser = serializer.HandlerLoggerListSerializer(page, many=True)
            return self.get_paginated_response(ser.data)

        ser = serializer.HandlerLoggerListSerializer(queryset, many=True)
        return success(result=ser.data)

    def _filter_log_params(self, request, queryset):
        kwargs = dict()
        params = request.query_params.dict()
        request_option = params.pop('request_option', None)
        if request_option:
            option = self.logging_options.get(request_option, None)
            if option is not None:
                kwargs['request_option'] = option
        request_ip = params.get('request_ip', None)
        request_url = params.get('request_url', None)
        request_method: str = params.get('request_method', None)
        response_status = params.get('response_status', None)
        start_time = params.get('startTime', '2000-01-01 00:00:00')
        end_time = params.get('endTime', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        if request_ip:
            kwargs['request_ip'] = request_ip
        if request_url:
            kwargs['request_url'] = request_url
        if request_method:
            kwargs['request_method'] = request_method
        if response_status:
            kwargs['response_status'] = response_status

        queryset = queryset.filter(created_at__range=[start_time, end_time], **kwargs)
        return queryset

    def get_response_code(self, request):
        status_map = [{'label': k, 'value': v}for k, v in globals().items() if k.startswith('HTTP')]
        return success(result=status_map)


class AuthAPIView(CreateAPIView):
    authentication_classes = []

    def post(self, request):
        ser = UserAuthSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        u, t = ser.create_token()
        u_ser = serializer.UserListSerializer(instance=u, many=False)
        result = u_ser.data
        result.update({"token": t})
        return other_response(message="η»ε½ζε", code=200, result=result)


class RoleModelViewSet(GenericViewSet,
                       mixins.CreateModelMixin,
                       mixins.ListModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.RetrieveModelMixin):
    queryset = models.Role.objects.all()
    serializer_class = serializer.RoleListSerializer
    authentication_classes = [Authentication]
    permission_classes = [IsAdminPermission]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializer.RoleListSerializer
        else:
            return serializer.AddRoleSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        else:
            return [permission() for permission in self.permission_classes]

    def get_authenticators(self):
        if self.request.method == "GET":
            return []
        else:
            return [auth() for auth in self.authentication_classes]

    def retrieve(self, request, *args, **kwargs):
        result = super().retrieve(request, *args, **kwargs)
        return success(result=result.data)

    def create(self, request, *args, **kwargs):
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        self.perform_create(create_serializer)

        ser = serializer.RoleListSerializer(instance=create_serializer.instance, many=False)
        return other_response(result=ser.data, code=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        u_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        u_serializer.is_valid(raise_exception=True)
        self.perform_update(u_serializer)
        result = serializer.RoleListSerializer(instance=u_serializer.instance, many=False)
        return success(message="δΏ?ζΉζε", result=result.data)


class PermissionViewSet(GenericViewSet,
                        mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        mixins.UpdateModelMixin,
                        ):
    queryset = models.Permission.objects.all()
    serializer_class = serializer.PermissionListSerializer
    authentication_classes = [Authentication]
    permission_classes = [IsAdminPermission]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return serializer.PermissionListSerializer
        else:
            return serializer.AddPermissionSerializer

    def get_authenticators(self):
        if self.request.method == "GET":
            return []
        else:
            return [auth() for auth in self.authentication_classes]

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        else:
            return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        self.perform_create(create_serializer)
        ser = serializer.PermissionListSerializer(instance=create_serializer.instance, many=False)
        return success(result=ser.data)


class ChangePasswordViewSet(APIView):
    """Change User Password"""
    required_fields = ['row_password', 'new_password', 'new_password_again']

    def post(self, request: Request):
        user = request.user
        data = request.data
        for f in filter(lambda x: not x[1], [(field, data.get(field, None)) for field in self.required_fields]):
            return other_response(message=f'{f[0]} δΈθ½δΈΊη©Ί', code=400, result={})
        if data.get('new_password') != data.get('new_password_again'):
            return other_response(message="δΈ€ζ¬‘ε―η δΈδΈθ΄", code=400, result={})
        if not user.verify_password(data.get('row_password')):
            return other_response(message="εε§ε―η ιθ――", code=400, result={})
        try:
            user.password = user.make_password(data.get('new_password'))
            user.save()
        except Exception as e:
            logger.error(e)
            return other_response(message=f"ζ°ζ?εΊιθ――οΌ{e}", code=400)
        return success(result={}, message="ε―η δΏ?ζζε")
