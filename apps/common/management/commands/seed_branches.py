"""Seed Branch / Cabang data."""
from django.core.management.base import BaseCommand
from apps.inventory.models import Branch

BRANCHES = [
    {
        'name': 'Toko Pusat Adikarya',
        'address': 'Jl. Raya Darmo No. 45, Surabaya',
        'manager': 'Ahmad Fauzi',
        'phone': '031-5678901',
        'email': 'pusat@adikarya.co',
    },
    {
        'name': 'Cabang Sidoarjo',
        'address': 'Jl. Ahmad Yani No. 120, Sidoarjo',
        'manager': 'Budi Santoso',
        'phone': '031-8901234',
        'email': 'sidoarjo@adikarya.co',
    },
]


class Command(BaseCommand):
    help = 'Seed branch data'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true')

    def handle(self, *args, **options):
        if options['flush']:
            Branch.objects.all().delete()
            self.stdout.write(self.style.WARNING('  Flushed branches'))

        for data in BRANCHES:
            obj, created = Branch.objects.update_or_create(
                name=data['name'], defaults=data)
            tag = 'CREATED' if created else 'UPDATED'
            self.stdout.write(f'  [{tag}] Branch: {obj.name}')

        self.stdout.write(self.style.SUCCESS(
            f'  Done — {Branch.objects.count()} branches total'))
