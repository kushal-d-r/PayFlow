
from rest_framework import serializers

from .models import PurchaseOrder, PurchaseOrderItem


class PurchaseOrderItemSerializer(serializers.ModelSerializer):

    subtotal = serializers.ReadOnlyField()
    tax_amount = serializers.ReadOnlyField()
    total_amount = serializers.ReadOnlyField()

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "id",
            "line_number",
            "item_code",
            "description",
            "unit_of_measure",
            "quantity",
            "unit_price",
            "tax_rate",
            "subtotal",
            "tax_amount",
            "total_amount",
        ]
        read_only_fields = ["id", "subtotal", "tax_amount", "total_amount"]


class PurchaseOrderSerializer(serializers.ModelSerializer):

    items = PurchaseOrderItemSerializer(many=True)

    vendor_name = serializers.CharField(
        source="vendor.legal_name",
        read_only=True
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True
    )

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "po_number",
            "vendor",
            "vendor_name",
            "order_date",
            "expected_delivery_date",
            "currency",
            "status",
            "notes",
            "items",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        order_date = attrs.get(
            "order_date",
            getattr(self.instance, "order_date", None)
        )

        expected_date = attrs.get(
            "expected_delivery_date",
            getattr(self.instance, "expected_delivery_date", None)
        )

        if expected_date and order_date and expected_date < order_date:
            raise serializers.ValidationError({
                "expected_delivery_date":
                    "Expected delivery date cannot be before order date."
            })

        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items")

        purchase_order = PurchaseOrder.objects.create(**validated_data)

        PurchaseOrderItem.objects.bulk_create([
            PurchaseOrderItem(
                purchase_order=purchase_order,
                **item_data
            )
            for item_data in items_data
        ])

        return purchase_order

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if items_data is not None:
            instance.items.all().delete()

            PurchaseOrderItem.objects.bulk_create([
                PurchaseOrderItem(
                    purchase_order=instance,
                    **item_data
                )
                for item_data in items_data
            ])

        return instance
