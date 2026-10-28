from django.contrib import admin

from .models import Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = (
        "vendor_code",
        "legal_name",
        "gstin",
        "city",
        "status",
        "created_at",
    )

    list_filter = ("status", "state")
    search_fields = (
        "vendor_code",
        "legal_name",
        "display_name",
        "gstin",
        "pan",
        "email",
    )

    readonly_fields = ("created_at", "updated_at")

    ordering = ("legal_name",)

    fieldsets = (
        ("Vendor Identification", {
            "fields": (
                "vendor_code",
                "legal_name",
                "display_name",
            )
        }),
        ("Tax Information", {
            "fields": ("gstin", "pan")
        }),
        ("Contact Information", {
            "fields": (
                "contact_person",
                "email",
                "phone",
            )
        }),
        ("Address", {
            "fields": (
                "address_line1",
                "address_line2",
                "city",
                "state",
                "postal_code",
            )
        }),
        ("Payment Terms and Status", {
            "fields": (
                "payment_terms_days",
                "status",
            )
        }),
        ("Audit Information", {
            "fields": (
                "created_by",
                "created_at",
                "updated_at",
            )
        }),
    )