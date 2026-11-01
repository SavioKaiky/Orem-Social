from rest_framework import serializers

from .models import Notification, Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "beneficiary", "purpose", "method", "amount", "dependents_count",
            "status", "txid", "pix_copy_paste", "expires_at", "paid_at", "created_at",
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "read_at", "created_at"]
        read_only_fields = fields