# inventory/models.py
from django.db import models
from common.models import TimeStampedModel

class Branch(TimeStampedModel):
    name = models.CharField(max_length=100)
    address = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Product(TimeStampedModel):
    PRODUCT_TYPES = [('PRODUCT', 'Produk Fisik'), ('SERVICE', 'Jasa/Layanan')]
    
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPES, default='GOODS')
    
    # Cost & Pricing
    base_price = models.DecimalField(max_digits=12, decimal_places=2, default=0) # Moving Average
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Metadata
    min_stock = models.IntegerField(default=2)

    def __str__(self):
        return self.name
    
    @property
    def total_stock(self):
        """Menghitung total stok dari seluruh cabang."""
        return sum(s.quantity for s in self.branch_stocks.all())

    def needs_restock(self):
        """Mengecek apakah stok sudah di bawah batas minimum."""
        return self.total_stock <= self.min_stock

    class Meta:
        verbose_name = "Produk & Jasa"

class Stock(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='branch_stocks')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='stock_levels')
    quantity = models.IntegerField(default=0)
    
    def add_stock(self, amount):
        self.quantity += amount
        self.save()

    def reduce_stock(self, amount):
        if self.quantity >= amount:
            self.quantity -= amount
            self.save()
            return True
        return False # Stok tidak cukup

    class Meta:
        unique_together = ('product', 'branch')