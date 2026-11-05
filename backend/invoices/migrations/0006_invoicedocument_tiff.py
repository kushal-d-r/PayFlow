from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0005_invoice_purchase_order_invoiceitem"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invoicedocument",
            name="document_type",
            field=models.CharField(
                choices=[("PDF", "PDF"), ("JPEG", "JPEG"), ("PNG", "PNG"), ("TIFF", "TIFF")],
                max_length=10,
            ),
        ),
    ]
