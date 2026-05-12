# transaction/models.py
from django.db import models
from apps.common.models import TimeStampedModel


class TransactionHeader(TimeStampedModel):
    TYPES = [('SALE', 'Penjualan'), ('PURCHASE', 'Pembelian')]
    METHODS = [('CASH', 'Tunai'), ('CREDIT', 'Tempo/Hutang')]

    invoice_number = models.CharField(max_length=50, unique=True)
    branch = models.ForeignKey('inventory.Branch', on_delete=models.PROTECT)
    contact = models.ForeignKey('partner.Contact', on_delete=models.PROTECT)

    trx_type = models.CharField(max_length=10, choices=TYPES)
    payment_method = models.CharField(max_length=10, choices=METHODS)

    total_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0)
    amount_paid = models.DecimalField(
        max_digits=15, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)

    is_finalized = models.BooleanField(default=False)

    def __str__(self):
        return self.invoice_number


class TransactionDetail(models.Model):
    header = models.ForeignKey(
        TransactionHeader, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
    related_service_ticket = models.ForeignKey(
        'service.ServiceTicket',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transaction_items',
    )
    qty = models.PositiveIntegerField()
    price_at_trx = models.DecimalField(max_digits=12, decimal_places=2)
    # Snapshot HPP tepat pada saat itu
    cost_at_trx = models.DecimalField(max_digits=12, decimal_places=2)
