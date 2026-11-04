from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from purchase_orders.models import PurchaseOrder, PurchaseOrderItem
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

    items = GoodsReceiptItemSerializer(many=True, allow_empty=False)

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

    @transaction.atomic
    def create(self, validated_data):

        items_data = validated_data.pop("items")

        # Lock the PO so concurrent GRN requests cannot exceed its quantity.
        purchase_order = PurchaseOrder.objects.select_for_update().get(
            pk=validated_data["purchase_order"].pk
        )

        if purchase_order.status not in [
            PurchaseOrder.Status.ISSUED,
            PurchaseOrder.Status.PARTIALLY_RECEIVED,
        ]:
            raise serializers.ValidationError({
                "purchase_order": (
                    "Goods receipts can only be created for Issued "
                    "or Partially Received purchase orders."
                )
            })

        # Lock all items belonging to this PO.
        po_items = list(
            PurchaseOrderItem.objects.select_for_update().filter(
                purchase_order=purchase_order
            )
        )

        if not po_items:
            raise serializers.ValidationError({
                "purchase_order": "This purchase order has no items."
            })

        po_items_by_id = {
            item.id: item for item in po_items
        }

        # Calculate quantities already received for each PO item.
        existing_totals = (
            GoodsReceiptItem.objects.filter(
                purchase_order_item__purchase_order=purchase_order
            )
            .values("purchase_order_item_id")
            .annotate(total_received=Sum("received_quantity"))
        )

        received_by_item = {
            row["purchase_order_item_id"]: row["total_received"]
            for row in existing_totals
        }

        requested_by_item = {}

        # Validate all incoming GRN items.
        for item_data in items_data:

            po_item = item_data["purchase_order_item"]

            if po_item.id not in po_items_by_id:
                raise serializers.ValidationError({
                    "items": (
                        f"PO item {po_item.id} does not belong "
                        "to the selected purchase order."
                    )
                })

            if po_item.id in requested_by_item:
                raise serializers.ValidationError({
                    "items": (
                        f"PO item {po_item.id} appears more than once "
                        "in this goods receipt."
                    )
                })

            requested_quantity = item_data["received_quantity"]

            already_received = received_by_item.get(
                po_item.id, 0
            ) or 0

            cumulative_quantity = (
                already_received + requested_quantity
            )

            if cumulative_quantity > po_item.quantity:
                remaining = po_item.quantity - already_received

                raise serializers.ValidationError({
                    "items": (
                        f"Over-receipt for PO item {po_item.id}. "
                        f"Ordered: {po_item.quantity}, "
                        f"Already received: {already_received}, "
                        f"Remaining: {remaining}, "
                        f"Requested: {requested_quantity}."
                    )
                })

            requested_by_item[po_item.id] = requested_quantity

        # Create GRN and its items.
        validated_data["purchase_order"] = purchase_order

        goods_receipt = GoodsReceipt.objects.create(
            **validated_data
        )

        GoodsReceiptItem.objects.bulk_create([
            GoodsReceiptItem(
                goods_receipt=goods_receipt,
                **item_data
            )
            for item_data in items_data
        ])

        # Recalculate total received quantity for every PO item.
        updated_totals = (
            GoodsReceiptItem.objects.filter(
                purchase_order_item__purchase_order=purchase_order
            )
            .values("purchase_order_item_id")
            .annotate(total_received=Sum("received_quantity"))
        )

        total_received_by_item = {
            row["purchase_order_item_id"]: row["total_received"]
            for row in updated_totals
        }

        all_items_fully_received = all(
            total_received_by_item.get(item.id, 0) >= item.quantity
            for item in po_items
        )

        any_quantity_received = any(
            total_received_by_item.get(item.id, 0) > 0
            for item in po_items
        )

        if all_items_fully_received:
            purchase_order.status = PurchaseOrder.Status.FULLY_RECEIVED

        elif any_quantity_received:
            purchase_order.status = PurchaseOrder.Status.PARTIALLY_RECEIVED

        else:
            purchase_order.status = PurchaseOrder.Status.ISSUED

        purchase_order.save(update_fields=["status", "updated_at"])

        return goods_receipt