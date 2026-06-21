"""Seed FinancialAccount & FinanceCategory data."""
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.finance.models import FinancialAccount, FinanceCategory

ACCOUNTS = [
    {'name': 'Kas Toko', 'account_type': 'CASH',
     'account_number': '', 'balance': Decimal('0')},
    {'name': 'Bank Jatim', 'account_type': 'BANK',
     'account_number': '0012345678', 'balance': Decimal('0')},
    {'name': 'Bank BCA', 'account_type': 'BANK',
     'account_number': '7890123456', 'balance': Decimal('0')},
    {'name': 'Investasi', 'account_type': 'INVESTMENT',
     'account_number': 'DEP-2025-001', 'balance': Decimal('0')},
    {'name': 'Modal Pemilik', 'account_type': 'EQUITY',
     'account_number': '', 'balance': Decimal('0')},
]

CATEGORIES = [
    # Pemasukan
    {'name': 'Penjualan Produk', 'category_type': 'INCOME'},
    {'name': 'Pendapatan Jasa Service', 'category_type': 'INCOME'},
    {'name': 'Pendapatan Jasa Rakit PC', 'category_type': 'INCOME'},
    {'name': 'Pendapatan Lain-lain', 'category_type': 'INCOME'},
    # Pengeluaran
    {'name': 'Pembelian Barang Dagang', 'category_type': 'EXPENSE'},
    {'name': 'Gaji Karyawan', 'category_type': 'EXPENSE'},
    {'name': 'Sewa Tempat', 'category_type': 'EXPENSE'},
    {'name': 'Listrik & Internet', 'category_type': 'EXPENSE'},
    {'name': 'Biaya Operasional', 'category_type': 'EXPENSE'},
    {'name': 'Biaya Transportasi', 'category_type': 'EXPENSE'},
    {'name': 'Biaya Admin Bank', 'category_type': 'EXPENSE'},
    # Aset
    {'name': 'Pembelian Aset Tetap', 'category_type': 'ASSET'},
    {'name': 'Penyusutan Aset', 'category_type': 'ASSET'},
    # Modal
    {'name': 'Setoran Modal', 'category_type': 'EQUITY'},
    {'name': 'Penarikan Prive', 'category_type': 'EQUITY'},
]


class Command(BaseCommand):
    help = 'Seed financial accounts & categories'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true')

    def handle(self, *args, **options):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE TABLE finance_financialaccount CASCADE')
            cursor.execute('TRUNCATE TABLE finance_financecategory CASCADE')
        self.stdout.write(self.style.WARNING('  Truncated finance data'))

        for data in ACCOUNTS:
            obj, created = FinancialAccount.objects.update_or_create(
                name=data['name'], defaults=data)
            tag = 'CREATED' if created else 'UPDATED'
            self.stdout.write(
                f'  [{tag}] Account: {obj.name} ({obj.account_type}) '
                f'= Rp{obj.balance:,.0f}')

        for data in CATEGORIES:
            obj, created = FinanceCategory.objects.update_or_create(
                name=data['name'], defaults=data)
            tag = 'CREATED' if created else 'UPDATED'
            self.stdout.write(f'  [{tag}] Category: {obj.name}')

        self.stdout.write(self.style.SUCCESS(
            f'  Done — {FinancialAccount.objects.count()} accounts, '
            f'{FinanceCategory.objects.count()} categories'))
