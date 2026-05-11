from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.finance.models import PaymentLog
from apps.inventory.models import Branch, Product
from apps.partner.models import Contact

from .models import TransactionHeader
from .services import (
    PurchaseService,
    SalesService,
    get_or_create_guest_customer,
)


def _normalize_money(value):
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalize_money_fields(obj, fields):
    for field in fields:
        setattr(obj, field, _normalize_money(getattr(obj, field, 0)))
    return obj


class PurchaseListView(View):
    template_name = "purchase/purchase_list.html"

    def get(self, request):
        queryset = (
            TransactionHeader.objects.filter(trx_type="PURCHASE")
            .select_related("contact", "branch")
            .order_by("-created_at")
        )
        filtered = PurchaseService.apply_filters(queryset, request.GET)

        paginator = Paginator(filtered, 10)
        purchases = paginator.get_page(request.GET.get("page"))
        for purchase in purchases.object_list:
            PurchaseService.attach_ui_fields(purchase)
            _normalize_money_fields(
                purchase,
                ("total_amount", "amount_paid", "outstanding"),
            )

        context = {
            "purchases": purchases,
            "suppliers": Contact.objects.filter(
                contact_type__in=["SUPPLIER", "BOTH"]
            ).order_by("name"),
            **PurchaseService.stats(),
        }
        return render(request, self.template_name, context)


class PurchaseCreateView(View):
    template_name = "purchase/purchase_create.html"

    def get(self, request):
        from django.db.models import Sum
        from django.db.models.functions import Coalesce
        import json

        products_qs = Product.objects.annotate(
            total_stock_count=Coalesce(Sum("branch_stocks__quantity"), 0)
        ).order_by("name")
        products_json = json.dumps([
            {
                "id": p.pk,
                "name": p.name,
                "sku": p.sku,
                "base_price": str(_normalize_money(p.base_price)),
                "selling_price": str(_normalize_money(p.selling_price)),
                "stock": p.total_stock_count,
            }
            for p in products_qs
        ])
        context = {
            "suppliers": Contact.objects.filter(
                contact_type__in=["SUPPLIER", "BOTH"]
            ).order_by("name"),
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
            "products": products_qs,
            "products_json": products_json,
            "today": timezone.now().date().isoformat(),
            "default_due_date": timezone.now().date() + timedelta(days=7),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        supplier_id = request.POST.get("supplier")
        branch_id = request.POST.get("branch")
        if not supplier_id or not branch_id:
            messages.error(request, "Supplier dan cabang wajib diisi.")
            return redirect("transaction:purchase_create")

        supplier = get_object_or_404(Contact, pk=supplier_id)
        branch = get_object_or_404(Branch, pk=branch_id)

        items, errors = PurchaseService.parse_items(request.POST)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("transaction:purchase_create")

        shipping = Decimal(request.POST.get("shipping_cost") or "0")
        other_fees = Decimal(request.POST.get("other_fees") or "0")
        landed_total = shipping + other_fees

        payment_method_raw = (request.POST.get("payment_method") or "").upper()
        payment_method = "CREDIT" if payment_method_raw == "CREDIT" else "CASH"

        amount_paid_raw = request.POST.get("amount_paid") or "0"
        try:
            amount_paid = Decimal(amount_paid_raw)
        except Exception:
            amount_paid = Decimal("0")

        due_date_raw = request.POST.get("due_date") or ""
        due_date = None
        if due_date_raw:
            try:
                due_date = date.fromisoformat(due_date_raw)
            except ValueError:
                due_date = None

        invoice_number = PurchaseService.generate_invoice_number()
        header = PurchaseService.create_purchase(
            invoice_number=invoice_number,
            supplier=supplier,
            branch=branch,
            payment_method=payment_method,
            due_date=due_date,
            items=items,
            landed_total=landed_total,
            created_by=request.user if request.user.is_authenticated else None,
        )

        if amount_paid > 0 and payment_method == "CREDIT":
            PurchaseService.record_payment(
                header=header,
                amount=amount_paid,
                note="Pembayaran awal saat pembelian.",
            )

        messages.success(request, "Purchase berhasil disimpan.")
        return redirect("transaction:purchase_detail", pk=header.pk)


class PurchaseDetailView(View):
    template_name = "purchase/purchase_detail.html"

    def get(self, request, pk):
        purchase = get_object_or_404(
            TransactionHeader.objects.select_related("contact", "branch"), pk=pk
        )
        PurchaseService.attach_ui_fields(purchase)
        items = purchase.items.select_related("product").all()
        items_subtotal = Decimal("0")
        for item in items:
            item.subtotal = item.qty * item.price_at_trx
            items_subtotal += item.subtotal
            item.landed_unit = item.cost_at_trx - item.price_at_trx
            _normalize_money_fields(
                item,
                ("price_at_trx", "cost_at_trx", "landed_unit", "subtotal"),
            )
        payments = purchase.paymentlog_set.order_by("-payment_date")

        landed_total = max(purchase.total_amount -
                           items_subtotal, Decimal("0"))

        _normalize_money_fields(
            purchase,
            ("total_amount", "amount_paid", "outstanding"),
        )
        items_subtotal = _normalize_money(items_subtotal)
        landed_total = _normalize_money(landed_total)

        context = {
            "purchase": purchase,
            "items": items,
            "payments": payments,
            "items_subtotal": items_subtotal,
            "landed_total": landed_total,
        }
        return render(request, self.template_name, context)


class PurchasePayablesView(View):
    template_name = "purchase/purchase_payable.html"

    def get(self, request):
        base_qs = (
            TransactionHeader.objects.filter(
                trx_type="PURCHASE", total_amount__gt=F("amount_paid")
            )
            .select_related("contact", "branch")
            .order_by("-due_date", "-created_at")
        )

        queryset = base_qs

        keyword = (request.GET.get("q") or "").strip()
        if keyword:
            queryset = queryset.filter(
                Q(invoice_number__icontains=keyword)
                | Q(contact__name__icontains=keyword)
            )

        status = (request.GET.get("status") or "").strip()
        today = timezone.now().date()
        if status == "overdue":
            queryset = queryset.filter(due_date__lt=today)
        elif status == "pending":
            queryset = queryset.filter(amount_paid=0)
        elif status == "partial":
            queryset = queryset.filter(amount_paid__gt=0)

        supplier = (request.GET.get("supplier") or "").strip()
        if supplier.isdigit():
            queryset = queryset.filter(contact_id=int(supplier))

        due_before = request.GET.get("due_before")
        if due_before:
            queryset = queryset.filter(due_date__lte=due_before)

        paginator = Paginator(queryset, 10)
        payables = paginator.get_page(request.GET.get("page"))
        for payable in payables.object_list:
            PurchaseService.attach_ui_fields(payable)
            _normalize_money_fields(
                payable,
                ("total_amount", "amount_paid", "outstanding"),
            )

        today = timezone.now().date()
        total_outstanding = base_qs.aggregate(
            total=Coalesce(
                Sum(F("total_amount") - F("amount_paid")), Decimal("0"))
        )["total"]
        overdue_total = base_qs.filter(due_date__lt=today).aggregate(
            total=Coalesce(
                Sum(F("total_amount") - F("amount_paid")), Decimal("0"))
        )["total"]
        week_due = base_qs.filter(due_date__range=(today, today + timedelta(days=7))).aggregate(
            total=Coalesce(
                Sum(F("total_amount") - F("amount_paid")), Decimal("0"))
        )["total"]
        paid_month = PaymentLog.objects.filter(
            payment_date__month=today.month,
            payment_date__year=today.year,
            transaction__trx_type="PURCHASE",
        ).aggregate(total=Coalesce(Sum("amount_paid"), Decimal("0")))["total"]
        outstanding_count = base_qs.count()

        total_outstanding = _normalize_money(total_outstanding)
        overdue_total = _normalize_money(overdue_total)
        week_due = _normalize_money(week_due)
        paid_month = _normalize_money(paid_month)

        context = {
            "payables": payables,
            "suppliers": Contact.objects.filter(
                contact_type__in=["SUPPLIER", "BOTH"]
            ).order_by("name"),
            "total_outstanding": total_outstanding,
            "overdue_total": overdue_total,
            "week_due": week_due,
            "paid_month": paid_month,
            "outstanding_count": outstanding_count,
        }
        return render(request, self.template_name, context)


class PurchasePayView(View):
    def post(self, request):
        invoice_number = request.POST.get("po_number")
        amount_raw = request.POST.get("amount")
        if not invoice_number or not amount_raw:
            messages.error(request, "Nomor invoice dan jumlah wajib diisi.")
            return redirect("transaction:purchase_payables")

        purchase = get_object_or_404(
            TransactionHeader, invoice_number=invoice_number, trx_type="PURCHASE"
        )
        try:
            amount = Decimal(amount_raw)
        except Exception:
            messages.error(request, "Jumlah pembayaran tidak valid.")
            return redirect("transaction:purchase_payables")

        method = request.POST.get("method") or ""
        reference = request.POST.get("reference") or ""
        notes = request.POST.get("notes") or ""
        note_parts = [p for p in [method, reference, notes] if p]
        note = " | ".join(note_parts)

        PurchaseService.record_payment(
            header=purchase, amount=amount, note=note)
        messages.success(request, "Pembayaran hutang berhasil disimpan.")
        return redirect("transaction:purchase_payables")


class PurchaseExportView(View):
    def get(self, request):
        queryset = (
            TransactionHeader.objects.filter(trx_type="PURCHASE")
            .select_related("contact", "branch")
            .order_by("-created_at")
        )
        filtered = PurchaseService.apply_filters(queryset, request.GET)
        return PurchaseService.build_export_response(filtered)


class PurchasePayablesExportView(View):
    def get(self, request):
        queryset = (
            TransactionHeader.objects.filter(
                trx_type="PURCHASE", total_amount__gt=F("amount_paid")
            )
            .select_related("contact", "branch")
            .order_by("-due_date")
        )
        return PurchaseService.build_export_response(queryset)


class PurchasePrintView(View):
    def get(self, request, pk):
        purchase = get_object_or_404(
            TransactionHeader.objects.select_related("contact", "branch"), pk=pk
        )
        PurchaseService.attach_ui_fields(purchase)
        items = purchase.items.select_related("product").all()
        context = {
            "purchase": purchase,
            "items": items,
            "is_print": True,
        }
        return render(request, "purchase/purchase_detail.html", context)


class SalesListView(View):
    template_name = "sale/sale_list.html"

    def get(self, request):
        queryset = (
            TransactionHeader.objects.filter(trx_type="SALE")
            .select_related("contact", "branch")
            .order_by("-created_at")
        )
        filtered = SalesService.apply_filters(queryset, request.GET)

        paginator = Paginator(filtered, 10)
        sales = paginator.get_page(request.GET.get("page"))
        for sale in sales.object_list:
            SalesService.attach_ui_fields(sale)
            _normalize_money_fields(
                sale,
                ("total_amount", "amount_paid", "outstanding"),
            )

        # Receivable stats for stat cards
        outstanding_qs = TransactionHeader.objects.filter(
            trx_type="SALE", total_amount__gt=F("amount_paid")
        )
        total_receivable = outstanding_qs.aggregate(
            total=Coalesce(
                Sum(F("total_amount") - F("amount_paid")), Decimal("0"))
        )["total"]
        outstanding_count = outstanding_qs.count()

        # Customers total (all time)
        stat_customers_all = Contact.objects.filter(
            contact_type__in=["CUSTOMER", "BOTH"]
        ).count()

        # Revenue month-to-date
        today = timezone.now().date()
        month_start = today.replace(day=1)
        stat_revenue_mtd = (
            queryset.filter(created_at__date__gte=month_start)
            .aggregate(total=Coalesce(Sum("total_amount"), Decimal("0")))
            ["total"]
        )

        context = {
            "sales": sales,
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
            "total_receivable": int(total_receivable),
            "outstanding_count": outstanding_count,
            "stat_customers_all": stat_customers_all,
            "stat_revenue_mtd": int(stat_revenue_mtd),
            **SalesService.stats(),
        }
        return render(request, self.template_name, context)


class SalesCreateView(View):
    template_name = "sale/sale_pos.html"

    def get(self, request):
        from django.db.models import Sum
        from django.db.models.functions import Coalesce
        import json

        products_qs = Product.objects.annotate(
            total_stock_count=Coalesce(Sum("branch_stocks__quantity"), 0)
        ).order_by("name")
        products_json = json.dumps(
            [
                {
                    "id": p.pk,
                    "name": p.name,
                    "sku": p.sku,
                    "selling_price": str(_normalize_money(p.selling_price)),
                    "stock": int(p.total_stock_count or 0),
                }
                for p in products_qs
            ]
        )
        context = {
            "customers": Contact.objects.filter(
                contact_type__in=["CUSTOMER", "BOTH"]
            ).order_by("name"),
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
            "products": products_qs,
            "products_json": products_json,
            "today": timezone.now().date().isoformat(),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        branch_id = request.POST.get("branch")
        if not branch_id:
            messages.error(request, "Cabang wajib diisi.")
            return redirect("transaction:sales_pos")

        branch = get_object_or_404(Branch, pk=branch_id)
        customer_id = (request.POST.get("customer") or "").strip()
        customer = (
            get_object_or_404(Contact, pk=customer_id)
            if customer_id
            else get_or_create_guest_customer()
        )

        items, errors = SalesService.parse_items(request.POST)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("transaction:sales_pos")

        payment_method_raw = (request.POST.get("payment_method") or "").lower()
        is_credit = request.POST.get("is_credit") == "1"
        payment_method = "CREDIT" if (
            payment_method_raw == "credit" or is_credit) else "CASH"

        due_date_raw = request.POST.get("due_date") or ""
        due_date = None
        if due_date_raw:
            try:
                due_date = date.fromisoformat(due_date_raw)
            except ValueError:
                due_date = None

        items_total = sum((item.subtotal for item in items), Decimal("0"))
        amount_paid = Decimal("0")
        if payment_method == "CREDIT":
            amount_paid_raw = request.POST.get("dp_amount") or "0"
            try:
                amount_paid = Decimal(amount_paid_raw)
            except Exception:
                amount_paid = Decimal("0")
            if amount_paid > items_total:
                amount_paid = items_total
        else:
            amount_paid = items_total

        invoice_number = SalesService.generate_invoice_number()
        try:
            header = SalesService.create_sale(
                invoice_number=invoice_number,
                customer=customer,
                branch=branch,
                payment_method=payment_method,
                due_date=due_date,
                items=items,
                amount_paid=amount_paid,
                created_by=request.user if request.user.is_authenticated else None,
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("transaction:sales_pos")

        messages.success(request, "Transaksi penjualan berhasil disimpan.")
        return redirect("transaction:sales_detail", pk=header.pk)


class SalesDetailView(View):
    template_name = "sale/sale_detail.html"

    def get(self, request, pk):
        sale = get_object_or_404(
            TransactionHeader.objects.select_related("contact", "branch"), pk=pk
        )
        SalesService.attach_ui_fields(sale)
        items = sale.items.select_related("product").all()
        for item in items:
            item.subtotal = item.qty * item.price_at_trx
            item.margin = item.price_at_trx - item.cost_at_trx
            _normalize_money_fields(
                item,
                ("price_at_trx", "cost_at_trx", "subtotal", "margin"),
            )
        payments = sale.paymentlog_set.order_by("-payment_date")
        for payment in payments:
            _normalize_money_fields(payment, ("amount_paid",))

        _normalize_money_fields(
            sale,
            ("total_amount", "amount_paid", "outstanding"),
        )

        context = {
            "sale": sale,
            "items": items,
            "payments": payments,
        }
        return render(request, self.template_name, context)


class SalesReceivablesView(View):
    template_name = "sale/sale_receivable.html"

    def get(self, request):
        base_qs = (
            TransactionHeader.objects.filter(
                trx_type="SALE", total_amount__gt=F("amount_paid")
            )
            .select_related("contact", "branch")
            .order_by("-due_date", "-created_at")
        )

        queryset = base_qs
        keyword = (request.GET.get("q") or "").strip()
        if keyword:
            queryset = queryset.filter(
                Q(invoice_number__icontains=keyword)
                | Q(contact__name__icontains=keyword)
            )

        status = (request.GET.get("status") or "").strip()
        today = timezone.now().date()
        if status == "overdue":
            queryset = queryset.filter(due_date__lt=today)
        elif status == "pending":
            queryset = queryset.filter(amount_paid=0)
        elif status == "partial":
            queryset = queryset.filter(amount_paid__gt=0)

        customer = (request.GET.get("customer") or "").strip()
        if customer.isdigit():
            queryset = queryset.filter(contact_id=int(customer))

        due_before = request.GET.get("due_before")
        if due_before:
            queryset = queryset.filter(due_date__lte=due_before)

        paginator = Paginator(queryset, 10)
        receivables = paginator.get_page(request.GET.get("page"))
        for receivable in receivables.object_list:
            SalesService.attach_ui_fields(receivable)
            _normalize_money_fields(
                receivable,
                ("total_amount", "amount_paid", "outstanding"),
            )

        total_receivable = base_qs.aggregate(
            total=Coalesce(
                Sum(F("total_amount") - F("amount_paid")), Decimal("0"))
        )["total"]
        overdue_total = base_qs.filter(due_date__lt=today).aggregate(
            total=Coalesce(
                Sum(F("total_amount") - F("amount_paid")), Decimal("0"))
        )["total"]
        week_due = base_qs.filter(due_date__range=(today, today + timedelta(days=7))).aggregate(
            total=Coalesce(
                Sum(F("total_amount") - F("amount_paid")), Decimal("0"))
        )["total"]
        collected_month = PaymentLog.objects.filter(
            payment_date__month=today.month,
            payment_date__year=today.year,
            transaction__trx_type="SALE",
        ).aggregate(total=Coalesce(Sum("amount_paid"), Decimal("0")))["total"]

        total_receivable = _normalize_money(total_receivable)
        overdue_total = _normalize_money(overdue_total)
        week_due = _normalize_money(week_due)
        collected_month = _normalize_money(collected_month)

        context = {
            "receivables": receivables,
            "customers": Contact.objects.filter(
                contact_type__in=["CUSTOMER", "BOTH"]
            ).order_by("name"),
            "total_receivable": total_receivable,
            "overdue_total": overdue_total,
            "week_due": week_due,
            "collected_month": collected_month,
        }
        return render(request, self.template_name, context)


class SalesPayView(View):
    def post(self, request):
        invoice_number = request.POST.get("invoice_number")
        amount_raw = request.POST.get("amount")
        if not invoice_number or not amount_raw:
            messages.error(request, "Nomor invoice dan jumlah wajib diisi.")
            return redirect("transaction:sales_receivables")

        sale = get_object_or_404(
            TransactionHeader, invoice_number=invoice_number, trx_type="SALE"
        )
        try:
            amount = Decimal(amount_raw)
        except Exception:
            messages.error(request, "Jumlah pembayaran tidak valid.")
            return redirect("transaction:sales_receivables")

        note = request.POST.get("notes") or ""
        SalesService.record_payment(header=sale, amount=amount, note=note)
        messages.success(request, "Pembayaran piutang berhasil disimpan.")
        return redirect("transaction:sales_receivables")


class SalesExportView(View):
    def get(self, request):
        queryset = (
            TransactionHeader.objects.filter(trx_type="SALE")
            .select_related("contact", "branch")
            .order_by("-created_at")
        )
        filtered = SalesService.apply_filters(queryset, request.GET)
        return SalesService.build_export_response(filtered)


class SalesPrintView(View):
    def get(self, request, pk):
        sale = get_object_or_404(
            TransactionHeader.objects.select_related("contact", "branch"), pk=pk
        )
        SalesService.attach_ui_fields(sale)
        items = sale.items.select_related("product").all()
        context = {
            "sale": sale,
            "items": items,
            "is_print": True,
        }
        return render(request, "sale/sale_detail.html", context)
