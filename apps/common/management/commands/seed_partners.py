"""Seed Contact (Customer & Supplier) data."""
from django.core.management.base import BaseCommand
from apps.partner.models import Contact

CONTACTS = [
    # --- SUPPLIERS ---
    {'name': 'PT Synnex Metrodata Indonesia', 'contact_type': 'SUPPLIER',
     'whatsapp': '021-29345678', 'address': 'Jakarta Selatan',
     'email': 'order@synnex.co.id'},
    {'name': 'PT Astrindo Starvision', 'contact_type': 'SUPPLIER',
     'whatsapp': '021-63856789', 'address': 'Jakarta Barat',
     'email': 'sales@astrindo.co.id'},
    {'name': 'PT Datascrip', 'contact_type': 'SUPPLIER',
     'whatsapp': '021-65309999', 'address': 'Jakarta Pusat',
     'email': 'order@datascrip.co.id'},
    {'name': 'CV Jaya Komputer Surabaya', 'contact_type': 'SUPPLIER',
     'whatsapp': '0812-3456-7890', 'address': 'Jl. Hitech Mall Lt.2, Surabaya',
     'email': 'jaya.komputer@gmail.com'},
    # --- CUSTOMERS ---
    {'name': 'Dinas Pendidikan Kota Surabaya', 'contact_type': 'CUSTOMER',
     'whatsapp': '031-5312144', 'address': 'Jl. Jagir Wonokromo, Surabaya'},
    {'name': 'SMA Negeri 5 Surabaya', 'contact_type': 'CUSTOMER',
     'whatsapp': '031-5921370', 'address': 'Jl. Kusuma Bangsa, Surabaya'},
    {'name': 'CV Maju Jaya', 'contact_type': 'CUSTOMER',
     'whatsapp': '0857-3456-1234', 'address': 'Jl. Rungkut Industri, Surabaya'},
    {'name': 'Rina Wulandari', 'contact_type': 'CUSTOMER',
     'whatsapp': '0813-5678-9012', 'address': 'Perum Graha Famili, Surabaya'},
    {'name': 'Hadi Prasetyo', 'contact_type': 'CUSTOMER',
     'whatsapp': '0856-4567-8901', 'address': 'Sidoarjo'},
    {'name': 'Warnet GG Gaming', 'contact_type': 'CUSTOMER',
     'whatsapp': '0878-1234-5678', 'address': 'Jl. Mulyosari, Surabaya'},
    # --- BOTH ---
    {'name': 'Toko Sinar Komputer', 'contact_type': 'BOTH',
     'whatsapp': '0821-9876-5432', 'address': 'Jl. Genteng Kali, Surabaya',
     'email': 'sinar.komputer@gmail.com'},
]


class Command(BaseCommand):
    help = 'Seed partner/contact data'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true')

    def handle(self, *args, **options):
        if options['flush']:
            Contact.objects.all().delete()
            self.stdout.write(self.style.WARNING('  Flushed contacts'))

        for data in CONTACTS:
            obj, created = Contact.objects.update_or_create(
                name=data['name'], defaults=data)
            tag = 'CREATED' if created else 'UPDATED'
            self.stdout.write(f'  [{tag}] {obj.contact_type}: {obj.name}')

        self.stdout.write(self.style.SUCCESS(
            f'  Done — {Contact.objects.count()} contacts total'))
