# -*- encoding: utf-8 -*-
"""
@File    : serializer.py
@Time    : 2022/4/8 下午1:49
@Author  : weidongkl
@Email   : weidong@uniontech.com
@Software: PyCharm
"""
from rest_framework import serializers
from apps.vul.models import VulAddrModel


class VulAddrListSerializer(serializers.ModelSerializer):
    method_display = serializers.SerializerMethodField()
    headers = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = VulAddrModel
        fields = ["id", "name", "description", "method", "method_display", "url", "headers", "params", "body",
                  "authorization_type", "authorization_body","parser", "status", "is_edited"
                  ]

    def get_method_display(self, attr: VulAddrModel) -> int:
        return attr.get_method_display()

    def get_description(self, attr: VulAddrModel) -> str:
        return attr.description or '暂未填写'

    def get_headers(self, attr: VulAddrModel) -> str:
        if attr.is_edited:
            return attr.headers
        else:
            shadow_string = "x" * 12
            shadow_fields = ["token", "authorization"]
            display_headers = attr.headers.copy()
            for k, v in attr.headers.items():
                if k.lower() in shadow_fields:
                    display_headers[k] = shadow_string
            return display_headers


class VulAddrModifySerializer(serializers.ModelSerializer):
    authorization_body = serializers.JSONField(required=False)

    class Meta:
        model = VulAddrModel
        fields = ["name", "description", "method", "url", "headers", "params", "body", "authorization_type",
                  "authorization_body", "parser"
                  ]
