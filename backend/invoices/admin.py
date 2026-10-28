from django.contrib import admin

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "vendor",
        "invoice_date",
        "due_date",
        "total_amount",
        "status",
    )

    list_filter = ("status", "currency", "invoice_date")
    search_fields = ("invoice_number", "vendor__legal_name")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "invoice_date"
    ordering = ("-created_at",)