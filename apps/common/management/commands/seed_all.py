"""Master seeder — calls all individual seeders in dependency order."""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run all seeders in correct dependency order'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Delete existing seed data before re-seeding')

    def handle(self, *args, **options):
        if options['flush']:
            from apps.finance.models import FinancialTransaction, FinancialAccount, FinanceCategory
            from apps.transaction.models import TransactionDetail, TransactionHeader
            from apps.service.models import ServiceTicket
            from apps.inventory.models import Stock, Product, Branch
            from apps.partner.models import Contact

            self.stdout.write(self.style.WARNING('Flushing database...'))
            FinancialTransaction.objects.all().delete()
            TransactionDetail.objects.all().delete()
            ServiceTicket.objects.all().delete()
            TransactionHeader.objects.all().delete()
            Stock.objects.all().delete()
            Product.objects.all().delete()
            Contact.objects.all().delete()
            Branch.objects.all().delete()
            FinancialAccount.objects.all().delete()
            FinanceCategory.objects.all().delete()

        seeders = [
            'seed_branches',
            'seed_partners',
            'seed_products',
            'seed_finance',
            'seed_transactions',
            'seed_services',
        ]
        for name in seeders:
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n> Running {name}...'))
            call_command(name, flush=False)

        self.stdout.write(self.style.SUCCESS('\n[OK] All seeders completed.'))
