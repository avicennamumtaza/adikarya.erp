# service/models.py
from django.db import models
from common.models import TimeStampedModel

class ServiceTicket(TimeStampedModel):
    STATUS_CHOICES = [
        ('RECEIVED', 'Diterima'),
        ('DIAGNOSING', 'Pengecekan'),
        ('DONE', 'Selesai'),
        ('PICKED', 'Diambil'),
        ('CANCELLED', 'Batal')
    ]
    ticket_number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey('partner.Contact', on_delete=models.PROTECT)
    branch = models.ForeignKey('inventory.Branch', on_delete=models.PROTECT)
    
    device_name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, blank=True)
    complaint = models.TextField()
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='RECEIVED')
    
    # Hubungkan ke Finance/Invoice saat checkout
    transaction = models.OneToOneField(
        'transaction.TransactionHeader', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='service_info'
    )