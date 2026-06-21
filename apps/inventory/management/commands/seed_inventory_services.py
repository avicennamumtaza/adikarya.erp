from django.core.management.base import BaseCommand
from apps.inventory.models import Product

class Command(BaseCommand):
    help = 'Seed initial service data'

    def handle(self, *args, **options):
        services_data = [
            {
                "sku": "SRV-001",
                "name": "Jasa Service Ringan",
                "product_type": "SERVICE",
                "category": "Jasa",
                "selling_price": 50000,
                "notes": "Pembersihan dan pengecekan standar."
            },
            {
                "sku": "SRV-002",
                "name": "Jasa Service Berat",
                "product_type": "SERVICE",
                "category": "Jasa",
                "selling_price": 150000,
                "notes": "Perbaikan komponen internal atau masalah kompleks."
            },
            {
                "sku": "SRV-003",
                "name": "Jasa Pengecekan / Diagnosis",
                "product_type": "SERVICE",
                "category": "Jasa",
                "selling_price": 25000,
                "notes": "Hanya pengecekan tanpa perbaikan."
            },
            {
                "sku": "SRV-004",
                "name": "Jasa Ganti LCD",
                "product_type": "SERVICE",
                "category": "Jasa",
                "selling_price": 100000,
                "notes": "Biaya jasa pemasangan LCD baru (tidak termasuk sparepart)."
            },
            {
                "sku": "SRV-005",
                "name": "Jasa Ganti Baterai",
                "product_type": "SERVICE",
                "category": "Jasa",
                "selling_price": 75000,
                "notes": "Biaya jasa pemasangan baterai baru (tidak termasuk sparepart)."
            },
            {
                "sku": "SRV-006",
                "name": "Jasa Software / Flash / Re-install",
                "product_type": "SERVICE",
                "category": "Jasa",
                "selling_price": 100000,
                "notes": "Penanganan masalah sistem operasi atau aplikasi."
            },
            {
                "sku": "SRV-007",
                "name": "Jasa Cleaning & Maintenance",
                "product_type": "SERVICE",
                "category": "Jasa",
                "selling_price": 35000,
                "notes": "Pembersihan fisik unit secara menyeluruh."
            }
        ]

        created_count = 0
        updated_count = 0

        for data in services_data:
            product, created = Product.objects.update_or_create(
                sku=data['sku'],
                defaults=data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Successfully created service: {product.name}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"Successfully updated service: {product.name}"))

        self.stdout.write(self.style.SUCCESS(f"\nSummary: {created_count} created, {updated_count} updated."))
