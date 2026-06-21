"""Seed TransactionHeader, TransactionDetail & FinancialTransaction data."""
import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.inventory.models import Branch, Product
from apps.partner.models import Contact
from apps.transaction.models import TransactionHeader, TransactionDetail
from apps.finance.models import FinancialAccount, FinancialTransaction, FinanceCategory


def _inv_number(prefix, seq):
    return f'{prefix}-{timezone.now().strftime("%Y%m")}-{seq:04d}'


SALE_SCENARIOS = [
    # (customer_name, method, items: [(sku, qty)])
    ('Dinas Pendidikan Kota Surabaya', 'CREDIT', [
        ('LPT-001', 10), ('PRN-001', 5), ('AKS-001', 10), ('AKS-002', 10)]),
    ('SMA Negeri 5 Surabaya', 'CREDIT', [
        ('PC-001', 8), ('MON-001', 8), ('AKS-001', 8), ('AKS-002', 8)]),
    ('CV Maju Jaya', 'CASH', [
        ('PRN-001', 2), ('AKS-008', 4), ('AKS-009', 3)]),
    ('Rina Wulandari', 'CASH', [
        ('LPT-002', 1), ('AKS-006', 1)]),
    ('Hadi Prasetyo', 'CASH', [
        ('KMP-001', 2), ('KMP-003', 1)]),
    ('Warnet GG Gaming', 'CREDIT', [
        ('PC-003', 6), ('MON-002', 6), ('AKS-003', 6), ('NET-002', 1)]),
]

PURCHASE_SCENARIOS = [
    # (supplier_name, method, items: [(sku, qty, cost_override)])
    ('PT Synnex Metrodata Indonesia', 'CREDIT', [
        ('LPT-001', 10, 6800000), ('LPT-002', 8, 7200000), ('LPT-004', 5, 8500000)]),
    ('PT Astrindo Starvision', 'CASH', [
        ('PRN-001', 10, 3100000), ('PRN-002', 6, 2800000), ('PRN-003', 5, 2700000)]),
    ('PT Datascrip', 'CASH', [
        ('AKS-008', 30, 72000), ('AKS-009', 24, 72000)]),
    ('CV Jaya Komputer Surabaya', 'CASH', [
        ('KMP-001', 30, 280000), ('KMP-002', 15, 650000), ('KMP-003', 20, 280000),
        ('AKS-001', 30, 95000), ('AKS-002', 40, 55000)]),
]


class Command(BaseCommand):
    help = 'Seed sale & purchase transactions with financial records'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true')

    def handle(self, *args, **options):
        from apps.transaction.services import (
            create_sale, SalesItemInput, 
            create_purchase, PurchaseItemInput
        )

        if options['flush']:
            FinancialTransaction.objects.filter(ref_invoice__isnull=False).delete()
            TransactionDetail.objects.all().delete()
            TransactionHeader.objects.all().delete()
            self.stdout.write(self.style.WARNING('  Flushed transactions'))

        branch = Branch.objects.first()
        if not branch:
            self.stdout.write(self.style.ERROR('  No branch found.'))
            return

        products_by_sku = {p.sku: p for p in Product.objects.all()}
        contacts_by_name = {c.name: c for c in Contact.objects.all()}

        sale_seq = 1
        purchase_seq = 1
        now = timezone.now()

        # ── PURCHASES ──
        for supp_name, method, items_data in PURCHASE_SCENARIOS:
            contact = contacts_by_name.get(supp_name)
            if not contact:
                continue

            inv = _inv_number('PO', purchase_seq)
            purchase_seq += 1

            if TransactionHeader.objects.filter(invoice_number=inv).exists():
                self.stdout.write(f'  [SKIP] {inv} already exists')
                continue

            # Keep dates within the last 20 days
            trx_date = now - timedelta(days=random.randint(2, 20))
            due = (trx_date + timedelta(days=45)).date() if method == 'CREDIT' else None
            
            purchase_inputs = []
            for sku, qty, cost in items_data:
                product = products_by_sku.get(sku)
                if product:
                    purchase_inputs.append(PurchaseItemInput(
                        product=product, qty=qty, unit_cost=Decimal(str(cost))
                    ))

            if not purchase_inputs:
                continue

            total_amount = sum((item.subtotal for item in purchase_inputs), Decimal("0"))
            
            # Use TRANSFER for large amounts to avoid draining Kas Toko
            actual_method = method
            if method == 'CASH' and total_amount > Decimal('10000000'):
                actual_method = 'TRANSFER'
                
            paid = total_amount if actual_method in ['CASH', 'TRANSFER'] else Decimal("0")

            # Create purchase via Service layer
            header = create_purchase(
                invoice_number=inv,
                supplier=contact,
                branch=branch,
                payment_method=actual_method,
                due_date=due,
                items=purchase_inputs,
                landed_total=Decimal("0"),
            )
            
            # Backdate
            TransactionHeader.objects.filter(pk=header.pk).update(created_at=trx_date)
            FinancialTransaction.objects.filter(ref_invoice=header).update(date=trx_date)

            self.stdout.write(f'  [PURCHASE] {inv} — {contact.name} — Rp{total_amount:,.0f}')

        # ── SALES ──
        for cust_name, method, items_data in SALE_SCENARIOS:
            contact = contacts_by_name.get(cust_name)
            if not contact:
                continue

            inv = _inv_number('INV', sale_seq)
            sale_seq += 1

            if TransactionHeader.objects.filter(invoice_number=inv).exists():
                self.stdout.write(f'  [SKIP] {inv} already exists')
                continue

            # Keep dates within the last 15 days to ensure they appear in the current month's dashboard
            trx_date = now - timedelta(days=random.randint(0, 15))
            due = (trx_date + timedelta(days=30)).date() if method == 'CREDIT' else None
            
            sales_inputs = []
            for sku, qty in items_data:
                product = products_by_sku.get(sku)
                if product:
                    # Adjust qty dynamically if stock is insufficient to prevent errors
                    stock_obj = product.branch_stocks.filter(branch=branch).first()
                    available_stock = stock_obj.quantity if stock_obj else 0
                    actual_qty = min(qty, available_stock)
                    if actual_qty > 0:
                        sales_inputs.append(SalesItemInput(
                            product=product, qty=actual_qty, unit_price=product.selling_price
                        ))
            
            if not sales_inputs:
                continue

            total_amount = sum((item.subtotal for item in sales_inputs), Decimal("0"))
            paid = total_amount if method == 'CASH' else Decimal("0")

            # Create sale via Service layer (Clean Architecture)
            header = create_sale(
                invoice_number=inv,
                customer=contact,
                branch=branch,
                payment_method=method,
                due_date=due,
                items=sales_inputs,
                amount_paid=paid
            )

            # Backdate the header and financial transactions for realistic timeline
            TransactionHeader.objects.filter(pk=header.pk).update(created_at=trx_date)
            FinancialTransaction.objects.filter(ref_invoice=header).update(date=trx_date)

            self.stdout.write(f'  [SALE] {inv} — {contact.name} — Rp{total_amount:,.0f}')

        self.stdout.write(self.style.SUCCESS(
            f'  Done — {TransactionHeader.objects.count()} transactions'))
