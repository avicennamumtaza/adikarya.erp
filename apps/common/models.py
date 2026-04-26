# core/models.py
from django.db import models
from django.conf import settings

class TimeStampedModel(models.Model):
    """
    Abstract model untuk audit trail global.
    Semua model bisnis harus mewarisi model ini.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Mengetahui siapa yang input data sangat krusial untuk audit ERP
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    class Meta:
        abstract = True  # PENTING: Django tidak akan membuat tabel untuk model ini.