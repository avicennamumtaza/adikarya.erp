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

    PRIORITY_CHOICES = [
        ("NORMAL", "Normal"),
        ("URGENT", "Urgent"),
        ("EMERGENCY", "Emergency"),
    ]

    ticket_number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey("partner.Contact", on_delete=models.PROTECT)
    branch = models.ForeignKey("inventory.Branch", on_delete=models.PROTECT)
    # Store technician as plain name string instead of FK to user
    technician_name = models.CharField(max_length=150, blank=True, default="")

    checkin_date = models.DateField(null=True, blank=True)

    device_type = models.CharField(max_length=30, blank=True, default="")
    device_brand = models.CharField(max_length=100, blank=True, default="")
    device_model = models.CharField(max_length=100, blank=True, default="")
    device_name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, blank=True)
    device_color = models.CharField(max_length=100, blank=True, default="")

    completeness = models.JSONField(default=list, blank=True)
    completeness_notes = models.CharField(
        max_length=255, blank=True, default="")
    condition = models.JSONField(default=list, blank=True)

    complaint = models.TextField()
    initial_diagnosis = models.TextField(blank=True, default="")

    estimated_cost = models.DecimalField(
        max_digits=15, decimal_places=2, default=0)
    estimated_completion = models.DateField(null=True, blank=True)

    labor_description = models.CharField(
        max_length=255, blank=True, default="")
    invoice_notes = models.TextField(blank=True, default="")
    warranty_days = models.PositiveIntegerField(default=0)
    discount_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0)

    warranty_void_informed = models.BooleanField(default=False)
    customer_agreement = models.BooleanField(default=False)
    internal_notes = models.TextField(blank=True, default="")

    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="NORMAL"
    )

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


class ServiceWorkLog(TimeStampedModel):
    LOG_TYPES = [
        ("diagnosis", "Diagnosis"),
        ("repair_action", "Repair Action"),
        ("part_used", "Part Used"),
        ("waiting_note", "Waiting Note"),
        ("customer_contact", "Customer Contact"),
        ("qc_check", "QC Check"),
        ("completed", "Completed"),
    ]

    ticket = models.ForeignKey(
        ServiceTicket, on_delete=models.CASCADE, related_name="worklogs"
    )
    title = models.CharField(max_length=150, blank=True, default="")
    log_type = models.CharField(max_length=30, choices=LOG_TYPES)
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_worklogs",
    )
    note = models.TextField()

    class Meta:
        ordering = ["created_at"]
