from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.finance.services import FinanceService
from apps.finance.models import FinancialAccount
from apps.inventory.models import Product, Stock
from apps.partner.models import Contact

from .models import TransactionDetail, TransactionHeader

import hashlib


@dataclass
class PurchaseItemInput:
    product: Product
    qty: int
    unit_cost: Decimal

    @property
    def subtotal(self) -> Decimal:
        return Decimal(self.qty) * self.unit_cost


@dataclass
class SalesItemInput:
    product: Product
    qty: int
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0")

    @property
    def subtotal(self) -> Decimal:
        discount_factor = Decimal("1") - (self.discount_pct / Decimal("100"))
        return Decimal(self.qty) * self.unit_price * discount_factor


def generate_purchase_invoice_number() -> str:
    today = timezone.now().date()
    year = today.year
    latest = (
        TransactionHeader.objects.filter(
            trx_type="PURCHASE", invoice_number__startswith=f"PO-{year}-"
        )
        .order_by("-invoice_number")
        .first()
    )
    last_seq = 0
    if latest:
        try:
            last_seq = int(latest.invoice_number.split("-")[-1])
        except (ValueError, AttributeError, IndexError):
            last_seq = 0
    return f"PO-{year}-{last_seq + 1:04d}"


def generate_sales_invoice_number() -> str:
    today = timezone.now().date()
    year = today.year
    latest = (
        TransactionHeader.objects.filter(
            trx_type="SALE", invoice_number__startswith=f"INV-{year}-"
        )
        .order_by("-invoice_number")
        .first()
    )
    last_seq = 0
    if latest:
        try:
            last_seq = int(latest.invoice_number.split("-")[-1])
        except (ValueError, AttributeError, IndexError):
            last_seq = 0
    return f"INV-{year}-{last_seq + 1:04d}"


def parse_purchase_items(post_data) -> tuple[list[PurchaseItemInput], list[str]]:
    items: list[PurchaseItemInput] = []
    errors: list[str] = []

    indices = []
    for key in post_data.keys():
        if key.startswith("item_product_"):
            indices.append(key.split("_")[-1])

    for idx in sorted(set(indices)):
        product_text = (post_data.get(f"item_product_{idx}") or "").strip()
        qty_raw = (post_data.get(f"item_qty_{idx}") or "").strip()
        cost_raw = (post_data.get(f"item_cost_{idx}") or "").strip()

        if not product_text and not qty_raw and not cost_raw:
            continue

        if not product_text or not qty_raw or not cost_raw:
            errors.append(f"Item baris {idx} belum lengkap.")
            continue

        try:
            qty = int(qty_raw)
        except ValueError:
            errors.append(f"Qty baris {idx} tidak valid.")
            continue

        try:
            unit_cost = Decimal(cost_raw)
        except Exception:
            errors.append(f"Harga beli baris {idx} tidak valid.")
            continue

        product = Product.objects.filter(
            Q(sku__iexact=product_text) | Q(name__iexact=product_text)
        ).first()
        if product is None and product_text.isdigit():
            product = Product.objects.filter(pk=int(product_text)).first()

        if product is None:
            errors.append(f"Produk '{product_text}' tidak ditemukan.")
            continue

        if qty <= 0:
            errors.append(f"Qty baris {idx} harus lebih dari 0.")
            continue

        if unit_cost < 0:
            errors.append(f"Harga beli baris {idx} tidak boleh negatif.")
            continue

        items.append(PurchaseItemInput(
            product=product, qty=qty, unit_cost=unit_cost))

    if not items and not errors:
        errors.append("Minimal 1 item pembelian harus diisi.")

    return items, errors


def parse_sales_items(post_data) -> tuple[list[SalesItemInput], list[str]]:
    items: list[SalesItemInput] = []
    errors: list[str] = []

    indices = []
    for key in post_data.keys():
        if key.startswith("product_id_"):
            indices.append(key.split("_")[-1])
        elif key.startswith("item_product_"):
            indices.append(key.split("_")[-1])

    for idx in sorted(set(indices)):
        product_raw = (post_data.get(f"product_id_{idx}") or post_data.get(
            f"item_product_{idx}") or "").strip()
        qty_raw = (post_data.get(f"qty_{idx}") or post_data.get(
            f"item_qty_{idx}") or "").strip()
        price_raw = (post_data.get(f"price_{idx}") or post_data.get(
            f"item_price_{idx}") or "").strip()
        disc_raw = (post_data.get(f"disc_{idx}") or "0").strip()

        if not product_raw and not qty_raw and not price_raw:
            continue

        if not product_raw or not qty_raw or not price_raw:
            errors.append(f"Item baris {idx} belum lengkap.")
            continue

        try:
            qty = int(qty_raw)
        except ValueError:
            errors.append(f"Qty baris {idx} tidak valid.")
            continue

        try:
            unit_price = Decimal(price_raw)
        except Exception:
            errors.append(f"Harga jual baris {idx} tidak valid.")
            continue

        try:
            discount_pct = Decimal(disc_raw)
        except Exception:
            discount_pct = Decimal("0")

        product = None
        if product_raw.isdigit():
            product = Product.objects.filter(pk=int(product_raw)).first()
        if product is None:
            product = Product.objects.filter(
                Q(sku__iexact=product_raw) | Q(name__iexact=product_raw)
            ).first()

        if product is None:
            errors.append(f"Produk '{product_raw}' tidak ditemukan.")
            continue

        if qty <= 0:
            errors.append(f"Qty baris {idx} harus lebih dari 0.")
            continue

        if unit_price < 0:
            errors.append(f"Harga jual baris {idx} tidak boleh negatif.")
            continue

        if discount_pct < 0 or discount_pct > 100:
            errors.append(f"Diskon baris {idx} harus 0-100.")
            continue

        items.append(
            SalesItemInput(
                product=product,
                qty=qty,
                unit_price=unit_price,
                discount_pct=discount_pct,
            )
        )

    if not items and not errors:
        errors.append("Minimal 1 item penjualan harus diisi.")

    return items, errors


def allocate_landed_cost(
    items: Iterable[PurchaseItemInput], landed_total: Decimal
) -> list[dict[str, Decimal]]:
    items_list = list(items)
    if not items_list:
        return []

    subtotal = sum((item.subtotal for item in items_list), Decimal("0"))
    if subtotal <= 0 or landed_total <= 0:
        return [
            {"landed_unit": Decimal("0"), "unit_cost": item.unit_cost}
            for item in items_list
        ]

    allocations: list[dict[str, Decimal]] = []
    for item in items_list:
        ratio = (item.subtotal / subtotal) if subtotal else Decimal("0")
        landed_unit = (landed_total * ratio) / Decimal(item.qty)
        allocations.append(
            {"landed_unit": landed_unit, "unit_cost": item.unit_cost + landed_unit}
        )
    return allocations


def process_purchase_item(product, branch, qty_in, price_in):
    with transaction.atomic():
        stock_obj, _ = Stock.objects.select_for_update().get_or_create(
            product=product,
            branch=branch,
            defaults={"quantity": 0},
        )

        current_total_stock = int(product.total_stock or 0)
        current_hpp = product.base_price

        if current_total_stock <= 0:
            new_hpp = price_in
        else:
            total_value_old = Decimal(current_total_stock) * current_hpp
            total_value_new = total_value_old + \
                (Decimal(qty_in) * Decimal(price_in))
            total_qty_new = current_total_stock + qty_in
            new_hpp = total_value_new / Decimal(total_qty_new)

        product.base_price = new_hpp
        product.save(update_fields=["base_price", "updated_at"])

        stock_obj.quantity += qty_in
        stock_obj.save(update_fields=["quantity", "updated_at"])


def process_sale_item(product, branch, qty_out):
    with transaction.atomic():
        stock_obj, _ = Stock.objects.select_for_update().get_or_create(
            product=product,
            branch=branch,
            defaults={"quantity": 0},
        )

        if stock_obj.quantity < qty_out:
            raise ValueError(
                f"Stok {product.name} tidak cukup. Sisa {stock_obj.quantity}."
            )

        stock_obj.quantity -= qty_out
        stock_obj.save(update_fields=["quantity", "updated_at"])


def compute_payment_status(header: TransactionHeader, today: date | None = None) -> str:
    today = today or timezone.now().date()
    if header.total_amount and header.amount_paid >= header.total_amount:
        return "paid"
    if header.amount_paid > 0:
        return "partial"
    if header.payment_method == "CREDIT" and header.due_date and header.due_date < today:
        return "overdue"
    return "pending"


def attach_purchase_ui_fields(header: TransactionHeader) -> TransactionHeader:
    status = compute_payment_status(header)
    header.status = status
    header.status_label = {
        "paid": "Lunas",
        "partial": "Sebagian",
        "pending": "Pending",
        "overdue": "Overdue",
    }[status]
    header.status_badge = {
        "paid": "badge-paid",
        "partial": "badge-partial",
        "pending": "badge-pending",
        "overdue": "badge-overdue",
    }[status]
    header.outstanding = max(header.total_amount -
                             header.amount_paid, Decimal("0"))
    header.progress_pct = int(
        (header.amount_paid / header.total_amount) * 100
    ) if header.total_amount else 0

    supplier_name = header.contact.name if header.contact_id else ""
    initials = "".join([part[:1]
                       for part in supplier_name.split()[:2]]).upper()
    header.supplier_initials = initials or "?"
    header.supplier_tag = header.contact.instagram or "" if header.contact_id else ""

    palette = [
        "emerald", "blue", "purple", "amber", "rose", "teal", "indigo", "cyan"
    ]
    if supplier_name:
        digest = hashlib.md5(supplier_name.encode("utf-8")).digest()[0]
        header.ui_color = palette[digest % len(palette)]
    else:
        header.ui_color = "slate"
    return header


def attach_sale_ui_fields(header: TransactionHeader) -> TransactionHeader:
    status = compute_payment_status(header)
    header.status = status
    header.status_label = {
        "paid": "Lunas",
        "partial": "Sebagian",
        "pending": "Pending",
        "overdue": "Overdue",
    }[status]
    header.status_badge = {
        "paid": "badge-paid",
        "partial": "badge-partial",
        "pending": "badge-unpaid",
        "overdue": "badge-overdue",
    }[status]
    header.outstanding = max(header.total_amount -
                             header.amount_paid, Decimal("0"))
    header.progress_pct = int(
        (header.amount_paid / header.total_amount) * 100
    ) if header.total_amount else 0

    # Customer initials and avatar color for list display
    customer_name = header.contact.name if header.contact_id else ""
    initials = "".join([part[:1]
                       for part in customer_name.split()[:2]]).upper()
    header.customer_initials = initials or "?"

    palette = [
        "emerald", "blue", "purple", "amber", "rose", "teal", "indigo", "cyan"
    ]
    if customer_name:
        digest = hashlib.md5(customer_name.encode("utf-8")).digest()[0]
        header.ui_color = palette[digest % len(palette)]
    else:
        header.ui_color = "slate"

    return header


def apply_purchase_filters(base_qs, query_params):
    qs = base_qs
    keyword = (query_params.get("q") or "").strip()
    if keyword:
        qs = qs.filter(
            Q(invoice_number__icontains=keyword)
            | Q(contact__name__icontains=keyword)
        )

    supplier = (query_params.get("supplier") or "").strip()
    if supplier.isdigit():
        qs = qs.filter(contact_id=int(supplier))

    status = (query_params.get("status") or "").strip()
    today = timezone.now().date()
    if status == "paid":
        qs = qs.filter(total_amount__lte=F("amount_paid"))
    elif status == "pending":
        qs = qs.filter(amount_paid=0)
    elif status == "partial":
        qs = qs.filter(amount_paid__gt=0, amount_paid__lt=F("total_amount"))
    elif status == "overdue":
        qs = qs.filter(amount_paid__lt=F("total_amount"), due_date__lt=today)

    date_from = (query_params.get("date_from") or "").strip()
    date_to = (query_params.get("date_to") or "").strip()
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    return qs


def apply_sales_filters(base_qs, query_params):
    qs = base_qs
    keyword = (query_params.get("q") or "").strip()
    if keyword:
        qs = qs.filter(
            Q(invoice_number__icontains=keyword)
            | Q(contact__name__icontains=keyword)
        )

    branch = (query_params.get("branch") or "").strip()
    if branch.isdigit():
        qs = qs.filter(branch_id=int(branch))

    status = (query_params.get("status") or "").strip()
    today = timezone.now().date()
    if status == "paid":
        qs = qs.filter(total_amount__lte=F("amount_paid"))
    elif status == "pending":
        qs = qs.filter(amount_paid=0)
    elif status == "partial":
        qs = qs.filter(amount_paid__gt=0, amount_paid__lt=F("total_amount"))
    elif status == "overdue":
        qs = qs.filter(amount_paid__lt=F("total_amount"), due_date__lt=today)

    method = (query_params.get("method") or "").strip().lower()
    if method == "credit":
        qs = qs.filter(payment_method="CREDIT")
    elif method == "cash":
        qs = qs.filter(payment_method="CASH")

    date_from = (query_params.get("date_from") or "").strip()
    date_to = (query_params.get("date_to") or "").strip()
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    return qs


def purchase_stats() -> dict[str, int]:
    today = timezone.now().date()
    month_start = today.replace(day=1)

    base_qs = TransactionHeader.objects.filter(trx_type="PURCHASE")
    mtd_total = base_qs.filter(created_at__date__gte=month_start).aggregate(
        total=Coalesce(Sum("total_amount"), Decimal("0"))
    )["total"]

    outstanding_expr = F("total_amount") - F("amount_paid")
    outstanding = base_qs.filter(total_amount__gt=F("amount_paid")).aggregate(
        total=Coalesce(Sum(outstanding_expr), Decimal("0"))
    )["total"]

    received_today = base_qs.filter(created_at__date=today).count()
    active_suppliers = base_qs.values("contact_id").distinct().count()

    return {
        "stat_purchase_mtd": int(mtd_total),
        "stat_outstanding": int(outstanding),
        "stat_received_today": received_today,
        "stat_active_suppliers": active_suppliers,
    }


def sales_stats() -> dict[str, int]:
    today = timezone.now().date()
    base_qs = TransactionHeader.objects.filter(trx_type="SALE")
    revenue_today = base_qs.filter(created_at__date=today).aggregate(
        total=Coalesce(Sum("total_amount"), Decimal("0"))
    )["total"]

    profit_expr = ExpressionWrapper(
        (F("price_at_trx") - F("cost_at_trx")) * F("qty"),
        output_field=DecimalField(max_digits=15, decimal_places=2),
    )
    profit_today = TransactionDetail.objects.filter(
        header__trx_type="SALE",
        header__created_at__date=today,
    ).aggregate(total=Coalesce(Sum(profit_expr), Decimal("0")))["total"]

    trx_today = base_qs.filter(created_at__date=today).count()

    return {
        "stat_revenue_today": int(revenue_today),
        "stat_profit_today": int(profit_today),
        "stat_sales_today": trx_today,
    }


def build_purchase_export_response(qs):
    from django.http import HttpResponse

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="purchases.csv"'

    import csv

    writer = csv.writer(response)
    writer.writerow(
        [
            "Invoice",
            "Tanggal",
            "Supplier",
            "Cabang",
            "Total",
            "Dibayar",
            "Sisa",
            "Status",
        ]
    )

    for purchase in qs:
        attach_purchase_ui_fields(purchase)
        writer.writerow(
            [
                purchase.invoice_number,
                purchase.created_at.date().isoformat(),
                purchase.contact.name if purchase.contact_id else "",
                purchase.branch.name if purchase.branch_id else "",
                purchase.total_amount,
                purchase.amount_paid,
                purchase.outstanding,
                purchase.status_label,
            ]
        )

    return response


def build_sales_export_response(qs):
    from django.http import HttpResponse

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sales.csv"'

    import csv

    writer = csv.writer(response)
    writer.writerow(
        [
            "Invoice",
            "Tanggal",
            "Customer",
            "Cabang",
            "Total",
            "Dibayar",
            "Sisa",
            "Status",
        ]
    )

    for sale in qs:
        attach_sale_ui_fields(sale)
        writer.writerow(
            [
                sale.invoice_number,
                sale.created_at.date().isoformat(),
                sale.contact.name if sale.contact_id else "",
                sale.branch.name if sale.branch_id else "",
                sale.total_amount,
                sale.amount_paid,
                sale.outstanding,
                sale.status_label,
            ]
        )

    return response


def create_purchase(
    *,
    invoice_number: str,
    supplier: Contact,
    branch,
    payment_method: str,
    due_date,
    items: list[PurchaseItemInput],
    landed_total: Decimal,
    financial_account: FinancialAccount | None = None,
    created_by=None,
) -> TransactionHeader:
    allocations = allocate_landed_cost(items, landed_total)
    items_total = sum((item.subtotal for item in items), Decimal("0"))
    total_amount = items_total + landed_total
    amount_paid = total_amount if payment_method in ["CASH", "TRANSFER"] else Decimal("0")

    with transaction.atomic():
        header = TransactionHeader.objects.create(
            invoice_number=invoice_number,
            branch=branch,
            contact=supplier,
            trx_type="PURCHASE",
            payment_method=payment_method,
            total_amount=total_amount,
            amount_paid=Decimal("0"),
            due_date=due_date,
            is_finalized=True,
            created_by=created_by,
        )

        for item, allocation in zip(items, allocations):
            unit_cost = allocation["unit_cost"]
            TransactionDetail.objects.create(
                header=header,
                product=item.product,
                qty=item.qty,
                price_at_trx=item.unit_cost,
                cost_at_trx=unit_cost,
            )
            process_purchase_item(item.product, branch, item.qty, unit_cost)
            
        # outstanding = total_amount
        supplier.current_balance -= total_amount
        supplier.save(update_fields=["current_balance", "updated_at"])

        if amount_paid > 0:
            if not financial_account:
                acc_type = 'BANK' if payment_method.upper() == 'TRANSFER' else 'CASH'
                financial_account = FinancialAccount.objects.filter(account_type=acc_type, is_active=True).first()
            if not financial_account:
                financial_account = FinancialAccount.objects.filter(is_active=True).first()
                
            FinanceService.pay_payable(
                invoice=header,
                amount=amount_paid,
                source_account=financial_account,
                note="Pembayaran awal pembelian."
            )

    return header


def get_or_create_guest_customer() -> Contact:
    guest, _ = Contact.objects.get_or_create(
        name="Guest",
        defaults={
            "contact_type": "CUSTOMER",
            "whatsapp": "000",
            "address": "",
        },
    )
    return guest


def create_sale(
    *,
    invoice_number: str,
    customer: Contact,
    branch,
    payment_method: str,
    due_date,
    items: list[SalesItemInput],
    amount_paid: Decimal,
    financial_account: FinancialAccount | None = None,
    created_by=None,
) -> TransactionHeader:
    total_amount = sum((item.subtotal for item in items), Decimal("0"))
    if amount_paid > total_amount:
        amount_paid = total_amount

    with transaction.atomic():
        header = TransactionHeader.objects.create(
            invoice_number=invoice_number,
            branch=branch,
            contact=customer,
            trx_type="SALE",
            payment_method=payment_method,
            total_amount=total_amount,
            amount_paid=Decimal("0"),
            due_date=due_date,
            is_finalized=True,
            created_by=created_by,
        )

        for item in items:
            TransactionDetail.objects.create(
                header=header,
                product=item.product,
                qty=item.qty,
                price_at_trx=item.unit_price,
                cost_at_trx=item.product.base_price,
            )
            process_sale_item(item.product, branch, item.qty)

        customer.current_balance += total_amount
        customer.save(update_fields=["current_balance", "updated_at"])

        if amount_paid > 0:
            if not financial_account:
                acc_type = 'BANK' if payment_method.upper() == 'TRANSFER' else 'CASH'
                financial_account = FinancialAccount.objects.filter(account_type=acc_type, is_active=True).first()
            if not financial_account:
                financial_account = FinancialAccount.objects.filter(is_active=True).first()
                
            FinanceService.receive_receivable(
                invoice=header,
                amount=amount_paid,
                destination_account=financial_account,
                note="Pembayaran awal penjualan."
            )

    return header


def record_purchase_payment(
    *,
    header: TransactionHeader,
    amount: Decimal,
    financial_account: FinancialAccount | None = None,
    note: str = "",
) -> TransactionHeader:
    if amount <= 0:
        return header

    remaining = header.total_amount - header.amount_paid
    applied = amount if amount <= remaining else remaining

    if applied <= 0:
        return header

    with transaction.atomic():
        if not financial_account:
            financial_account = FinancialAccount.objects.filter(account_type='CASH', is_active=True).first()
        if not financial_account:
            financial_account = FinancialAccount.objects.filter(is_active=True).first()
            
        FinanceService.pay_payable(
            invoice=header,
            amount=applied,
            source_account=financial_account,
            note=note,
        )

    return header


def record_sale_payment(
    *,
    header: TransactionHeader,
    amount: Decimal,
    financial_account: FinancialAccount | None = None,
    note: str = "",
) -> TransactionHeader:
    if amount <= 0:
        return header

    remaining = header.total_amount - header.amount_paid
    applied = amount if amount <= remaining else remaining
    if applied <= 0:
        return header

    with transaction.atomic():
        if not financial_account:
            financial_account = FinancialAccount.objects.filter(account_type='CASH', is_active=True).first()
        if not financial_account:
            financial_account = FinancialAccount.objects.filter(is_active=True).first()
            
        FinanceService.receive_receivable(
            invoice=header,
            amount=applied,
            destination_account=financial_account,
            note=note,
        )

    return header


class PurchaseService:
    @staticmethod
    def generate_invoice_number() -> str:
        return generate_purchase_invoice_number()

    @staticmethod
    def parse_items(post_data):
        return parse_purchase_items(post_data)

    @staticmethod
    def create_purchase(**kwargs) -> TransactionHeader:
        return create_purchase(**kwargs)

    @staticmethod
    def record_payment(**kwargs) -> TransactionHeader:
        return record_purchase_payment(**kwargs)

    @staticmethod
    def apply_filters(base_qs, query_params):
        return apply_purchase_filters(base_qs, query_params)

    @staticmethod
    def attach_ui_fields(header: TransactionHeader) -> TransactionHeader:
        return attach_purchase_ui_fields(header)

    @staticmethod
    def stats() -> dict[str, int]:
        return purchase_stats()

    @staticmethod
    def build_export_response(qs):
        return build_purchase_export_response(qs)


class SalesService:
    @staticmethod
    def generate_invoice_number() -> str:
        return generate_sales_invoice_number()

    @staticmethod
    def parse_items(post_data):
        return parse_sales_items(post_data)

    @staticmethod
    def create_sale(**kwargs) -> TransactionHeader:
        return create_sale(**kwargs)

    @staticmethod
    def record_payment(**kwargs) -> TransactionHeader:
        return record_sale_payment(**kwargs)

    @staticmethod
    def apply_filters(base_qs, query_params):
        return apply_sales_filters(base_qs, query_params)

    @staticmethod
    def attach_ui_fields(header: TransactionHeader) -> TransactionHeader:
        return attach_sale_ui_fields(header)

    @staticmethod
    def stats() -> dict[str, int]:
        return sales_stats()

    @staticmethod
    def build_export_response(qs):
        return build_sales_export_response(qs)
