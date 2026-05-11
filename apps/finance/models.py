# finance/models.py
from django.db import models
from apps.common.models import TimeStampedModel


class PaymentLog(TimeStampedModel):
    """Mencatat setiap kali ada uang masuk/keluar untuk pelunasan invoice."""
    transaction = models.ForeignKey(
        'transaction.TransactionHeader', on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)
