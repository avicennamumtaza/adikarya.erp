from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class ServiceTicket(TimeStampedModel):
    STATUS_CHOICES = [
        ("RECEIVED", "Diterima"),
        ("DIAGNOSING", "Pengecekan"),
        ("WAITING", "Menunggu Part"),
        ("REPAIRING", "Perbaikan"),
        ("DONE", "Siap Diambil"),
        ("PICKED", "Diambil"),
        ("CANCELLED", "Batal"),
    ]

    ticket_number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey("partner.Contact", on_delete=models.PROTECT)
    branch = models.ForeignKey("inventory.Branch", on_delete=models.PROTECT)

    checkin_date = models.DateField(null=True, blank=True)

    device_type = models.CharField(max_length=30, blank=True, default="")
    device_brand = models.CharField(max_length=100, blank=True, default="")
    device_name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, blank=True)
    device_color = models.CharField(max_length=100, blank=True, default="")

    completeness = models.JSONField(default=list, blank=True)
    completeness_notes = models.CharField(
        max_length=255, blank=True, default="")
    condition = models.JSONField(default=list, blank=True)

    complaint = models.TextField()

    invoice_notes = models.TextField(blank=True, default="")
    warranty_days = models.PositiveIntegerField(default=0)
    discount_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0)

    customer_agreement = models.BooleanField(default=False)

    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="RECEIVED")

    # Hubungkan ke Finance/Invoice saat checkout
    transaction = models.OneToOneField(
        "transaction.TransactionHeader",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_info",
    )

    def __str__(self):
        return self.ticket_number
