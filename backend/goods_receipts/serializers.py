
from rest_framework import serializers

from .models import GoodsReceipt, GoodsReceiptItem


class GoodsReceiptItemSerializer(serializers.ModelSerializer):

    po_item_description = serializers.CharField(
        source="purchase_order_item.description",
        read_only=True
    )

    class Meta:
        model = GoodsReceiptItem
        fields = [
            "id",
            "purchase_order_item",
            "po_item_description",
            "received_quantity",
            "accepted_quantity",
            "rejected_quantity",
            "notes",
        ]

        read_only_fields = ["id"]

    def validate(self, attrs):
        received = attrs.get("received_quantity", 0)
        accepted = attrs.get("accepted_quantity", 0)
        rejected = attrs.get("rejected_quantity", 0)

        if accepted + rejected > received:
            raise serializers.ValidationError(
                "Accepted and rejected quantities cannot exceed received quantity."
            )

        return attrs


class GoodsReceiptSerializer(serializers.ModelSerializer):

    items = GoodsReceiptItemSerializer(many=True)

    po_number = serializers.CharField(
        source="purchase_order.po_number",
        read_only=True
    )

    received_by_username = serializers.CharField(
        source="received_by.username",
        read_only=True
    )

    class Meta:
        model = GoodsReceipt
        fields = [
            "id",
            "grn_number",
            "purchase_order",
            "po_number",
            "received_date",
            "status",
            "notes",
            "items",
            "received_by",
            "received_by_username",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "received_by",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        items_data = validated_data.pop("items")

        purchase_order = validated_data["purchase_order"]

        for item_data in items_data:
            po_item = item_data["purchase_order_item"]

            if po_item.purchase_order_id != purchase_order.id:
                raise serializers.ValidationError({
                    "items": (
                        f"PO item {po_item.id} does not belong "
                        "to the selected purchase order."
                    )
                })

        goods_receipt = GoodsReceipt.objects.create(**validated_data)

        GoodsReceiptItem.objects.bulk_create([
            GoodsReceiptItem(
                goods_receipt=goods_receipt,
                **item_data
            )
            for item_data in items_data
        ])

        return goods_receipt
