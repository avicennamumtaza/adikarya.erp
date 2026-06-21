# finance/models.py
from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel


class FinancialAccount(TimeStampedModel):
    ACCOUNT_TYPE_CHOICES = [
        ('CASH', 'Kas/Tunai'),
        ('BANK', 'Bank'),
        ('INVESTMENT', 'Investasi'),
        ('EQUITY', 'Modal/Ekuitas'),
    ]
    
    name = models.CharField(max_length=100) # Contoh: "BCA Operasional"
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    account_number = models.CharField(max_length=50, blank=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"


class FinanceCategory(TimeStampedModel):
    CATEGORY_TYPE_CHOICES = [
        ('INCOME', 'Pemasukan'),
        ('EXPENSE', 'Pengeluaran'),
        ('ASSET', 'Aset'),
        ('EQUITY', 'Modal'),
    ]
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPE_CHOICES)
    
    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"


class FinancialTransaction(TimeStampedModel):
    TRX_TYPE_CHOICES = [
        ('IN', 'Masuk (Pendapatan/Modal/Piutang)'),
        ('OUT', 'Keluar (Beban/Hutang/Investasi)'),
        ('TRANSFER', 'Transfer Antar Akun'),
    ]

    transaction_type = models.CharField(max_length=10, choices=TRX_TYPE_CHOICES)
    
    reference_number = models.CharField(max_length=50, blank=True, unique=True, null=True)

    source_account = models.ForeignKey(
        FinancialAccount, on_delete=models.PROTECT, null=True, blank=True, related_name='withdrawals')
    
    destination_account = models.ForeignKey(
        FinancialAccount, on_delete=models.PROTECT, null=True, blank=True, related_name='deposits')

    category = models.ForeignKey(FinanceCategory, on_delete=models.SET_NULL, null=True, blank=True)

    # Relasi ke TransactionHeader (Invoice)
    ref_invoice = models.ForeignKey(
        'transaction.TransactionHeader', on_delete=models.SET_NULL, null=True, blank=True, related_name='financial_transactions')

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    fee = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Biaya admin bank
    date = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True)
    
    is_void = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.date.strftime('%Y-%m-%d')}"


class PaymentLog(TimeStampedModel):
    """Mencatat setiap kali ada uang masuk/keluar untuk pelunasan invoice. (DEPRECATED)"""
    transaction = models.ForeignKey(
        'transaction.TransactionHeader', on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)
