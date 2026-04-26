# partner/models.py
from django.db import models
from common.models import TimeStampedModel # Asumsi Anda buat Base Model di core

class Contact(TimeStampedModel):
    CONTACT_TYPES = [('CUSTOMER', 'Customer'), ('SUPPLIER', 'Supplier'), ('BOTH', 'Keduanya')]
    
    name = models.CharField(max_length=150)
    contact_type = models.CharField(max_length=10, choices=CONTACT_TYPES)
    whatsapp = models.CharField(max_length=30)
    instagram = models.CharField(max_length=50, blank=True, null=True)
    facebook = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    
    # Financial snapshot
    # Positif: Piutang kita (Customer hutang)
    # Negatif: Hutang kita (Kita hutang ke Supplier)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} ({self.contact_type})"