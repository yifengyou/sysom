import logging
import re
from rest_framework.views import APIView
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import register_job
from tzlocal import get_localzone
from lib.response import *
from apps.accounts.authentication import Authentication
from apps.vul.models import *
from apps.vul.vul import update_sa as upsa, update_vul as upvul
from apps.vul.vul import fix_cve, get_unfix_cve

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone=get_localzone())


@register_job(scheduler, 'cron', id='update_vul', hour=0, minute=0)
def update_vul():
    upvul()


@register_job(scheduler, 'cron', id='update_sa', hour=2, minute=0)
def update_sa():
    upsa()


scheduler.start()


class VulListView(APIView):
    authentication_classes = [Authentication]

    def get(self, request, format=None):
        """
        Return a list of all users.
        """
        cves = SecurityAdvisoryModel.objects.exclude(host=None)
        cves_data = {}
        for cve in cves:
            cve_id = cve.cve_id
            if cves_data.get(cve_id):
                hosts = [host[0] for host in cve.host.all().values_list("hostname")]
                cves_data[cve_id]["hosts"] += hosts

            else:
                vul_level = cve.vul_level
                score = cve.score
                description = cve.description
                detail = cve.detail
                pub_time = cve.pub_time
                hosts = [host[0] for host in cve.host.all().values_list("hostname")]
                cves_data[cve_id] = {
                    "cve_id": cve_id,
                    "vul_level": vul_level,
                    "score": score,
                    "description": str(description),
                    "detail": detail,
                    "pub_time": pub_time,
                    "hosts": hosts,
                }
        data = list(cves_data.values())
        return success(result=data)

    def post(self, request, format=None):
        logger.error(request.user)
        failed = False
        data = []
        for cve in request.data.get("cve_id_list"):
            hosts = cve["hostname"]
            cve_id = cve["cve_id"]
            results = fix_cve(hosts, cve_id, user=request.user)
            logger.warning(results)
            sucess_host_list = []
            fail_host_list = []
            for ret in results:
                hostname = ret["host"]
                if ret["ret"]["status"] == 0:
                    sucess_host_list.append(hostname)
                else:
                    failed = True
                    fail_host_list.append({
                        "hosts": hostname,
                        "describe": str(ret["ret"]["result"])
                    })
            data.append({
                "cve_id": cve_id,
                "sucess_host_list": sucess_host_list,
                "fail_host_list": fail_host_list
            })
        logger.error(data)
        if failed:
            return other_response(message='fix cve failed', code=200, result=data)
        else:
            return success(result=data)


class VulDetailsView(APIView):
    authentication_classes = [Authentication]

    def get(self, request, cve_id, format=None):
        """
        Return a list of all users.
        """
        cve_re = "CVE-\d{4}-\d{4,7}"
        if re.match(cve_re, cve_id, re.I) is None:
            other_response(message='Illegal parameter', code=400)
        cves = SecurityAdvisoryModel.objects.exclude(host=None).filter(cve_id=cve_id)
        cves_data = {}
        flag = False
        for cve in cves:
            cve_id = cve.cve_id
            vul_level = cve.vul_level
            if flag:
                software_name = cve.software_name
                fixed_version = cve.fixed_version
                hosts = [self.get_host_info(host[0]) for host in cve.host.all().values_list("hostname")]
                cves_data["software"].append({
                    "name": software_name,
                    "vul_level": vul_level,
                    "fixed_version": fixed_version
                })
                cves_data["hosts"] += hosts

            else:
                flag = True
                score = cve.score
                description = cve.description
                detail = cve.detail
                pub_time = cve.pub_time
                software_name = cve.software_name
                fixed_version = cve.fixed_version
                hosts = [self.get_host_info(host[0]) for host in cve.host.all().values_list("hostname")]
                cves_data = {
                    "cve_id": cve_id,
                    "vul_level": vul_level,
                    "score": score,
                    "description": str(description),
                    "detail": detail,
                    "pub_time": pub_time,
                    "hosts": hosts,
                    "software": [{
                        "name": software_name,
                        "vul_level": vul_level,
                        "fixed_version": fixed_version
                    }]
                }
        data = cves_data
        return success(result=data)

    def get_host_info(self, hostname):
        host = HostModel.objects.filter(hostname=hostname).first()
        return {
            "hostname": hostname,
            "ip": host.ip,
            "created_by": host.created_by.username,
            "created_at": host.created_at,
            "status": host.get_status_display(),
        }


class VulSummaryView(APIView):
    authentication_classes = [Authentication]

    def get(self, request, format=None):
        """
        """
        sa = SecurityAdvisoryModel.objects.exclude(host=None)
        sa_cve_count, sa_high_cve_count, sa_affect_host_count = self.get_vul_info(sa)
        unfix_vul = get_unfix_cve().exclude(host=None)
        vul_cve_count, vul_high_cve_count, vul_affect_host_count = self.get_vul_info(unfix_vul)

        data = {
            "fixed_cve": {
                "affect_host_count": sa_affect_host_count,
                "cve_count": sa_cve_count,
                "high_cve_count": sa_high_cve_count,
            },

            "unfixed_cve": {
                "affected_host_number": vul_affect_host_count,
                "cve_number": vul_cve_count,
                "high_cve_number": vul_high_cve_count,
            }
        }
        return success(result=data)

    def get_vul_info(self, queryset):
        cve_count = len(set([cve[0] for cve in queryset.values_list("cve_id")]))
        high_cve_count = len(set([cve[0] for cve in queryset.filter(score__gt=7.0).values_list("cve_id")]))
        affect_host = []
        for cve in queryset:
            affect_host.extend(list(cve.host.all()))
        affect_host_count = len(set(affect_host))
        return cve_count, high_cve_count, affect_host_count


class SaFixHistListView(APIView):
    authentication_classes = [Authentication]

    def get(self, request, format=None):
        sa_fix_hist = SecurityAdvisoryFixHistoryModel.objects.all()
        data = [{"id": fix_obj.id,
                 "cve_id": fix_obj.cve_id,
                 "fixed_time": fix_obj.fixed_at,
                 "fix_user": fix_obj.created_by.username,
                 "status": fix_obj.status,
                 "vul_level": fix_obj.vul_level} for fix_obj in sa_fix_hist]
        return success(result=data)


class SaFixHistDetailsView(APIView):
    authentication_classes = [Authentication]

    def get_cve2host_details(self, sa_fix_host_obj):
        hostname = sa_fix_host_obj.host.hostname
        host = HostModel.objects.filter(hostname=hostname).first()
        return {
            "hostname": hostname,
            "ip": host.ip,
            "created_by": host.created_by.username,
            "created_at": host.created_at,
            "host_status": host.get_status_display(),
            "status": sa_fix_host_obj.status,
            "details": str(sa_fix_host_obj.details),
        }

    def get(self, request, pk, format=None):
        sa_fix_hist_details = SaFixHistToHost.objects.filter(sa_fix_hist_id=pk)
        data = [self.get_cve2host_details(detail_obj) for detail_obj in sa_fix_hist_details]
        for item in range(len(data)):
            data[item]["id"] = item + 1
        return success(result=data)


class SaFixHistDetailHostView(APIView):
    authentication_classes = [Authentication]

    def get(self, request, pk, hostname, format=None):
        sa_fix_hist_details_host = SaFixHistToHost.objects.filter(sa_fix_hist_id=pk, host__hostname=hostname).first()
        data = {
            "hostname": hostname,
            "status": sa_fix_hist_details_host.status,
            "details": str(sa_fix_hist_details_host.details),
        }
        return success(result=data)