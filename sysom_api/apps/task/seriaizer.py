# -*- encoding: utf-8 -*-
"""
@File    : seriaizer.py
@Time    : 2021/11/22 17:41
@Author  : DM
@Software: PyCharm
"""
from rest_framework import serializers
from apps.task.models import JobModel


class JobListSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobModel
        exclude = ('deleted_at', 'host_by', 'command', 'result')



class JobRetrieveSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobModel
        exclude = ('deleted_at', 'host_by', 'command')