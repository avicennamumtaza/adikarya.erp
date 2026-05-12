import csv
import re
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db import models
from django.db.models import F, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.inventory.models import Branch, Product, Stock
from apps.partner.models import Contact
from apps.transaction.models import TransactionDetail, TransactionHeader

from .models import ServiceTicket, ServiceWorkLog


User = get_user_model()


STATUS_UI = {
    "RECEIVED": {"label": "Received", "badge": "badge-received", "dot": "bg-slate-400"},
    "DIAGNOSING": {"label": "Diagnosing", "badge": "badge-diagnosing", "dot": "bg-blue-500"},
    "WAITING": {"label": "Waiting", "badge": "badge-waiting", "dot": "bg-amber-500"},
    "REPAIRING": {"label": "Repairing", "badge": "badge-repairing", "dot": "bg-violet-500"},
    "DONE": {"label": "Ready", "badge": "badge-ready", "dot": "bg-emerald-500"},
    "PICKED": {"label": "Picked", "badge": "badge-done", "dot": "bg-emerald-500"},
    "CANCELLED": {"label": "Cancelled", "badge": "badge-cancelled", "dot": "bg-red-500"},
}


def _as_decimal(value: str | None, default: Decimal = Decimal("0")) -> Decimal:
    if value is None:
        return default
    try:
        cleaned = str(value).strip().replace(".", "").replace(",", ".")
        if cleaned == "":
            return default
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return default


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return timezone.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _ticket_overdue_days(ticket: ServiceTicket):
    if not ticket.estimated_completion:
        return 0
    if ticket.status in {"DONE", "PICKED", "CANCELLED"}:
        return 0
    today = timezone.localdate()
    if ticket.estimated_completion >= today:
        return 0
    return (today - ticket.estimated_completion).days


def _initials(user_or_name):
    """Return initials for a User object or a plain name string."""
    if not user_or_name:
        return "-"
    # If given a plain string name
    if isinstance(user_or_name, str):
        parts = [p for p in user_or_name.split() if p]
        if parts:
            return "".join(p[0].upper() for p in parts[:2])
        return "-"
    # Otherwise treat as user-like object
    full = (
        f"{getattr(user_or_name, 'first_name', '')} {getattr(user_or_name, 'last_name', '')}"
    ).strip()
    if full:
        parts = [p for p in full.split() if p]
        return "".join(p[0].upper() for p in parts[:2])
    username = getattr(user_or_name, "username", "")
    return (username[:2] or "-").upper()


def _recalc_header_total(header: TransactionHeader) -> Decimal:
    total = (
        header.items.aggregate(
            total=Coalesce(
                Sum(
                    F("qty") * F("price_at_trx"),
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                ),
                Decimal("0"),
            )
        )["total"]
        or Decimal("0")
    )
    header.total_amount = total
    header.save(update_fields=["total_amount"])
    return total


def _get_or_create_labor_product() -> Product:
    product, _created = Product.objects.get_or_create(
        sku="SRV-LABOR",
        defaults={
            "name": "Jasa Servis",
            "product_type": "SERVICE",
            "base_price": Decimal("0"),
            "selling_price": Decimal("0"),
            "min_stock": 0,
        },
    )
    return product


def _parse_contact_from_partner_input(value: str | None) -> Contact | None:
    if not value:
        return None
    raw = str(value).strip()
    # Accept plain numeric ID
    if raw.isdigit():
        return Contact.objects.filter(pk=int(raw)).first()
    # Accept "<id> | <name>" format
    match = re.match(r"^(\d+)\s*[|\-]", raw)
    if match:
        return Contact.objects.filter(pk=int(match.group(1))).first()
    # Fallback: try name exact (last resort)
    return Contact.objects.filter(name__iexact=raw).first()


def _next_ticket_number() -> str:
    last = ServiceTicket.objects.filter(
        ticket_number__startswith="SRV-").order_by("-id").first()
    if not last:
        return "SRV-0001"
    m = re.search(r"(\d+)$", last.ticket_number or "")
    if not m:
        return "SRV-0001"
    nxt = int(m.group(1)) + 1
    width = max(4, len(m.group(1)))
    return f"SRV-{nxt:0{width}d}"


class ServiceQueueView(View):
    template_name = "service/service_queue.html"

    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        status = (request.GET.get("status") or "").strip()
        technician_id = _parse_int(request.GET.get("technician"))
        branch_id = _parse_int(request.GET.get("branch"))

        tickets = ServiceTicket.objects.select_related(
            "customer", "branch", "technician"
        ).order_by("-id")

        if branch_id:
            tickets = tickets.filter(branch_id=branch_id)
        if technician_id:
            tickets = tickets.filter(technician_id=technician_id)

        base_for_stats = tickets

        if status:
            if status == "overdue":
                today = timezone.localdate()
                tickets = tickets.filter(estimated_completion__lt=today).exclude(
                    status__in=["DONE", "PICKED", "CANCELLED"]
                )
            else:
                tickets = tickets.filter(status=status)

        if q:
            tickets = tickets.filter(
                models.Q(ticket_number__icontains=q)
                | models.Q(customer__name__icontains=q)
                | models.Q(device_name__icontains=q)
                | models.Q(serial_number__icontains=q)
                | models.Q(device_brand__icontains=q)
                | models.Q(device_model__icontains=q)
            )

        # Limit to keep page fast and allow attaching computed fields safely.
        tickets_list = list(tickets[:200])

        # Attach computed fields used by template
        for t in tickets_list:
            overdue_days = _ticket_overdue_days(t)
            setattr(t, "overdue_days", overdue_days)
            setattr(t, "is_overdue", overdue_days > 0)
            ui = STATUS_UI.get(
                t.status, {"label": t.status, "badge": "badge-received", "dot": "bg-slate-400"})
            setattr(t, "status_label", ui["label"])
            setattr(t, "status_badge", ui["badge"])
            setattr(t, "status_dot", ui["dot"])
            setattr(t, "technician_initials", _initials(t.technician))

        today = timezone.localdate()
        total_active = base_for_stats.exclude(
            status__in=["PICKED", "CANCELLED"]).count()
        waiting_parts = base_for_stats.filter(status="WAITING").count()
        ready_pickup = base_for_stats.filter(status="DONE").count()
        overdue_count = base_for_stats.filter(estimated_completion__lt=today).exclude(
            status__in=["DONE", "PICKED", "CANCELLED"]
        ).count()
        finished_today = base_for_stats.filter(
            status__in=["DONE", "PICKED"], updated_at__date=today
        ).count()

        context = {
            "tickets": tickets_list,
            "q": q,
            "status": status,
            "technician": technician_id or "",
            "branch": branch_id or "",
            "technicians": User.objects.filter(is_active=True).order_by("first_name", "username"),
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
            "stats": {
                "total_active": total_active,
                "waiting_parts": waiting_parts,
                "ready_pickup": ready_pickup,
                "overdue": overdue_count,
                "finished_today": finished_today,
            },
        }
        return render(request, self.template_name, context)


class ServiceCheckinView(View):
    template_name = "service/service_checkin.html"

    def get(self, request):
        context = {
            "preview_ticket_number": _next_ticket_number(),
            "today": timezone.localdate(),
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
            "technicians": User.objects.filter(is_active=True).order_by("first_name", "username"),
            "partners": Contact.objects.order_by("name")[:300],
        }
        return render(request, self.template_name, context)


class ServiceCheckinSaveView(View):
    def post(self, request):
        branch_id = _parse_int(request.POST.get(
            "branch_id") or request.POST.get("branch"))
        branch = Branch.objects.filter(
            pk=branch_id).first() if branch_id else None
        customer = _parse_contact_from_partner_input(
            request.POST.get("partner_id"))
        technician_id = _parse_int(request.POST.get(
            "technician_id") or request.POST.get("technician"))
        technician = User.objects.filter(
            pk=technician_id).first() if technician_id else None

        if not branch:
            messages.error(request, "Branch wajib dipilih.")
            return redirect("service:service_checkin")
        if not customer:
            messages.error(request, "Customer wajib dipilih.")
            return redirect("service:service_checkin")

        checkin_date = _parse_date(request.POST.get(
            "checkin_date")) or timezone.localdate()
        device_name = (request.POST.get("device_name") or "").strip()
        complaint = (request.POST.get("complaint") or "").strip()
        if not device_name or not complaint:
            messages.error(request, "Device name dan complaint wajib diisi.")
            return redirect("service:service_checkin")

        completeness = request.POST.getlist("completeness")
        condition = request.POST.getlist("condition")

        estimated_cost = _as_decimal(
            request.POST.get("estimated_cost"), Decimal("0"))
        estimated_completion = _parse_date(
            request.POST.get("estimated_completion"))

        priority = (request.POST.get("priority")
                    or "NORMAL").strip() or "NORMAL"

        warranty_void_informed = bool(
            request.POST.get("warranty_void_informed"))
        customer_agreement = bool(request.POST.get("customer_agreement"))

        action = (request.POST.get("action") or "save").strip()

        for _ in range(3):
            try:
                with transaction.atomic():
                    ticket_number = _next_ticket_number()
                    ticket = ServiceTicket.objects.create(
                        ticket_number=ticket_number,
                        customer=customer,
                        branch=branch,
                        technician=technician,
                        checkin_date=checkin_date,
                        device_type=(request.POST.get(
                            "device_type") or "").strip(),
                        device_brand=(request.POST.get(
                            "device_brand") or "").strip(),
                        device_model=(request.POST.get(
                            "device_model") or "").strip(),
                        device_name=device_name,
                        serial_number=(request.POST.get(
                            "serial_number") or "").strip(),
                        device_color=(request.POST.get(
                            "device_color") or "").strip(),
                        completeness=completeness,
                        completeness_notes=(request.POST.get(
                            "completeness_notes") or "").strip(),
                        condition=condition,
                        complaint=complaint,
                        initial_diagnosis=(request.POST.get(
                            "initial_diagnosis") or "").strip(),
                        estimated_cost=estimated_cost,
                        estimated_completion=estimated_completion,
                        priority=priority,
                        warranty_void_informed=warranty_void_informed,
                        customer_agreement=customer_agreement,
                        internal_notes=(request.POST.get(
                            "internal_notes") or "").strip(),
                        created_by=request.user if getattr(
                            request.user, "is_authenticated", False) else None,
                        updated_by=request.user if getattr(
                            request.user, "is_authenticated", False) else None,
                    )

                    header = TransactionHeader.objects.create(
                        invoice_number=f"INV-{ticket_number}",
                        branch=branch,
                        contact=customer,
                        trx_type="SALE",
                        payment_method="CASH",
                        total_amount=Decimal("0"),
                        amount_paid=Decimal("0"),
                        is_finalized=False,
                        created_by=request.user if getattr(
                            request.user, "is_authenticated", False) else None,
                        updated_by=request.user if getattr(
                            request.user, "is_authenticated", False) else None,
                    )
                    ticket.transaction = header
                    ticket.save(update_fields=["transaction"])

                    ServiceWorkLog.objects.create(
                        ticket=ticket,
                        title="Unit Check-in",
                        log_type="repair_action",
                        technician=technician,
                        note=complaint,
                        created_by=request.user if getattr(
                            request.user, "is_authenticated", False) else None,
                        updated_by=request.user if getattr(
                            request.user, "is_authenticated", False) else None,
                    )
                messages.success(request, f"Check-in saved: {ticket_number}")
                if action == "save_print":
                    return redirect("service:service_print_tag", pk=ticket.pk)
                return redirect("service:service_detail", pk=ticket.pk)
            except IntegrityError:
                continue

        messages.error(request, "Gagal membuat ticket. Silakan coba lagi.")
        return redirect("service:service_checkin")


class ServiceExportView(View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="service_tickets.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "ticket_number",
                "status",
                "priority",
                "checkin_date",
                "customer",
                "whatsapp",
                "device",
                "serial_number",
                "branch",
                "technician",
                "estimated_completion",
            ]
        )

        qs = ServiceTicket.objects.select_related(
            "customer", "branch", "technician").order_by("-id")
        for t in qs[:5000]:
            writer.writerow(
                [
                    t.ticket_number,
                    t.status,
                    t.priority,
                    t.checkin_date,
                    t.customer.name if t.customer_id else "",
                    t.customer.whatsapp if t.customer_id else "",
                    t.device_name,
                    t.serial_number,
                    t.branch.name if t.branch_id else "",
                    getattr(t.technician, "get_full_name", lambda: "")() or getattr(
                        t.technician, "username", "") if t.technician_id else "",
                    t.estimated_completion,
                ]
            )
        return response


class ServiceDetailView(View):
    def get(self, request, pk):
        ticket = get_object_or_404(
            ServiceTicket.objects.select_related(
                "customer", "branch", "technician", "transaction"),
            pk=pk,
        )
        header = ticket.transaction
        items = []
        if header_id := getattr(header, "id", None):
            items = list(
                TransactionDetail.objects.select_related("product").filter(
                    header_id=header_id, related_service_ticket=ticket
                )
            )

        labor_product = _get_or_create_labor_product()
        labor_item = next(
            (i for i in items if i.product_id == labor_product.id), None)
        parts_items = [i for i in items if i.product.product_type != "SERVICE"]

        for i in items:
            setattr(i, "line_total", (i.price_at_trx or 0) * i.qty)

        parts_total = sum((i.line_total for i in parts_items), Decimal("0"))
        labor_total = labor_item.line_total if labor_item else Decimal("0")
        discount = ticket.discount_amount or Decimal("0")
        estimated_total = parts_total + labor_total - discount
        if estimated_total < 0:
            estimated_total = Decimal("0")

        stock_map = {}
        if ticket.branch_id and parts_items:
            product_ids = {i.product_id for i in parts_items}
            for s in Stock.objects.filter(branch_id=ticket.branch_id, product_id__in=product_ids):
                stock_map[s.product_id] = s.quantity

        for i in parts_items:
            stock_qty = stock_map.get(i.product_id)
            if stock_qty is None:
                i.stock_class = "stock-ok"
                i.stock_label = "Stok: —"
            elif stock_qty <= 0:
                i.stock_class = "stock-out"
                i.stock_label = f"Stok: {stock_qty}"
            elif stock_qty <= (i.product.min_stock or 0):
                i.stock_class = "stock-low"
                i.stock_label = f"Stok Rendah: {stock_qty}"
            else:
                i.stock_class = "stock-ok"
                i.stock_label = f"Stok: {stock_qty}"

        overdue_days = _ticket_overdue_days(ticket)
        ui = STATUS_UI.get(ticket.status, {
                           "label": ticket.status, "badge": "badge-received", "dot": "bg-slate-400"})
        setattr(ticket, "status_label", ui["label"])
        setattr(ticket, "status_badge", ui["badge"])
        setattr(ticket, "status_dot", ui["dot"])
        setattr(ticket, "overdue_days", overdue_days)
        # technician_initials now computed from plain name string
        setattr(ticket, "technician_initials", _initials(ticket.technician_name))

        context = {
            "ticket": ticket,
            "header": header,
            "worklogs": ticket.worklogs.select_related("technician").all(),
            "parts_items": parts_items,
            "labor_item": labor_item,
            "stock_map": stock_map,
            "parts_total": parts_total,
            "labor_total": labor_total,
            "discount": discount,
            "estimated_total": estimated_total,
            "technicians": User.objects.filter(is_active=True).order_by("first_name", "username"),
            "products": Product.objects.filter(product_type="PRODUCT").order_by("name")[:500],
        }
        return render(request, "service/service_detail.html", context)


class ServiceCheckinEditView(View):
    def get(self, request, pk):
        ticket = get_object_or_404(ServiceTicket.objects.select_related(
            "customer", "branch"), pk=pk)
        context = {
            "ticket": ticket,
            "today": timezone.localdate(),
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
            "technicians": User.objects.filter(is_active=True).order_by("first_name", "username"),
            "partners": Contact.objects.order_by("name")[:300],
        }
        return render(request, "service/service_checkin.html", context)

    def post(self, request, pk):
        ticket = get_object_or_404(
            ServiceTicket.objects.select_related("transaction"), pk=pk)
        branch_id = _parse_int(request.POST.get(
            "branch_id") or request.POST.get("branch"))
        branch = Branch.objects.filter(
            pk=branch_id).first() if branch_id else None
        customer = _parse_contact_from_partner_input(
            request.POST.get("partner_id"))
        technician_id = _parse_int(request.POST.get(
            "technician_id") or request.POST.get("technician"))
        technician = User.objects.filter(
            pk=technician_id).first() if technician_id else None

        if not branch or not customer:
            messages.error(request, "Branch dan Customer wajib dipilih.")
            return redirect("service:service_checkin_edit", pk=ticket.pk)

        ticket.branch = branch
        ticket.customer = customer
        ticket.technician_name = technician.get_full_name() if technician else ""
        ticket.checkin_date = _parse_date(
            request.POST.get("checkin_date")) or ticket.checkin_date
        ticket.device_type = (request.POST.get("device_type") or "").strip()
        ticket.device_brand = (request.POST.get("device_brand") or "").strip()
        ticket.device_model = (request.POST.get("device_model") or "").strip()
        ticket.device_name = (request.POST.get(
            "device_name") or "").strip() or ticket.device_name
        ticket.serial_number = (request.POST.get(
            "serial_number") or "").strip()
        ticket.device_color = (request.POST.get("device_color") or "").strip()
        ticket.completeness = request.POST.getlist("completeness")
        ticket.completeness_notes = (request.POST.get(
            "completeness_notes") or "").strip()
        ticket.condition = request.POST.getlist("condition")
        ticket.complaint = (request.POST.get("complaint")
                            or "").strip() or ticket.complaint
        ticket.initial_diagnosis = (request.POST.get(
            "initial_diagnosis") or "").strip()
        ticket.estimated_cost = _as_decimal(
            request.POST.get("estimated_cost"), ticket.estimated_cost)
        ticket.estimated_completion = _parse_date(
            request.POST.get("estimated_completion"))
        ticket.priority = (request.POST.get("priority")
                           or ticket.priority).strip() or ticket.priority
        ticket.warranty_void_informed = bool(
            request.POST.get("warranty_void_informed"))
        ticket.customer_agreement = bool(
            request.POST.get("customer_agreement"))
        ticket.internal_notes = (request.POST.get(
            "internal_notes") or "").strip()
        ticket.updated_by = request.user if getattr(
            request.user, "is_authenticated", False) else None
        ticket.save()

        if ticket.transaction_id:
            TransactionHeader.objects.filter(pk=ticket.transaction_id).update(
                branch=branch,
                contact=customer,
                updated_by=request.user if getattr(
                    request.user, "is_authenticated", False) else None,
            )

        messages.success(request, "Check-in updated.")
        return redirect("service:service_detail", pk=ticket.pk)


class ServicePrintTagView(View):
    def get(self, request, pk):
        ticket = get_object_or_404(ServiceTicket.objects.select_related(
            "customer", "branch", "technician"), pk=pk)
        return render(request, "service/service_tag_print.html", {"ticket": ticket})


class ServiceBillingView(View):
    def get(self, request, pk):
        ticket = get_object_or_404(ServiceTicket.objects.select_related(
            "customer", "branch", "transaction"), pk=pk)
        header = ticket.transaction

        items = []
        if header_id := getattr(header, "id", None):
            items = list(
                TransactionDetail.objects.select_related("product").filter(
                    header_id=header_id, related_service_ticket=ticket
                )
            )
        for i in items:
            setattr(i, "line_total", (i.price_at_trx or 0) * i.qty)

        parts_items = [i for i in items if i.product.product_type != "SERVICE"]
        labor_items = [i for i in items if i.product.product_type == "SERVICE"]
        parts_total = sum((i.line_total for i in parts_items), Decimal("0"))
        labor_total = sum((i.line_total for i in labor_items), Decimal("0"))

        subtotal = sum((i.line_total for i in items), Decimal("0"))
        discount = ticket.discount_amount or Decimal("0")
        grand_total = subtotal - discount
        if grand_total < 0:
            grand_total = Decimal("0")

        amount_paid = header.amount_paid if header else Decimal("0")
        amount_paid_default = amount_paid if amount_paid > 0 else grand_total
        change_amount = amount_paid - grand_total
        if change_amount < 0:
            change_amount = Decimal("0")
        credit_remaining = grand_total - amount_paid
        if credit_remaining < 0:
            credit_remaining = Decimal("0")

        payment_method = getattr(header, "payment_method", "CASH") or "CASH"
        is_credit = payment_method == "CREDIT"

        context = {
            "ticket": ticket,
            "header": header,
            "items": items,
            "parts_items": parts_items,
            "parts_total": parts_total,
            "parts_count": len(parts_items),
            "labor_total": labor_total,
            "subtotal": subtotal,
            "discount": discount,
            "grand_total": grand_total,
            "amount_paid_default": amount_paid_default,
            "change_amount": change_amount,
            "credit_remaining": credit_remaining,
            "payment_method": payment_method,
            "is_credit": is_credit,
        }
        return render(request, "service/service_billing.html", context)


class ServiceUpdateStatusView(View):
    def post(self, request, pk):
        ticket = get_object_or_404(ServiceTicket, pk=pk)
        raw = (request.POST.get("status") or "").strip()
        status_map = {
            "received": "RECEIVED",
            "diagnosing": "DIAGNOSING",
            "waiting_parts": "WAITING",
            "waiting": "WAITING",
            "repairing": "REPAIRING",
            "ready": "DONE",
            "done": "DONE",
            "picked": "PICKED",
            "cancelled": "CANCELLED",
            "canceled": "CANCELLED",
        }
        status = status_map.get(raw.lower(), raw.upper())
        valid_status = {s for s, _ in ServiceTicket.STATUS_CHOICES}
        if status not in valid_status:
            messages.error(request, "Status tidak valid.")
            return redirect("service:service_detail", pk=ticket.pk)
        ticket.status = status
        ticket.updated_by = request.user if getattr(
            request.user, "is_authenticated", False) else None
        ticket.save(update_fields=["status", "updated_by", "updated_at"])
        messages.success(request, "Status updated.")
        return redirect("service:service_detail", pk=ticket.pk)


class ServiceAddLogView(View):
    def post(self, request, pk):
        ticket = get_object_or_404(ServiceTicket, pk=pk)
        title = (request.POST.get("title") or "").strip()
        log_type = (request.POST.get("log_type") or "repair_action").strip()
        note = (request.POST.get("note") or "").strip()
        tech_id = _parse_int(request.POST.get("technician_id"))
        technician = User.objects.filter(
            pk=tech_id).first() if tech_id else ticket.technician

        valid_types = {t for t, _ in ServiceWorkLog.LOG_TYPES}
        if log_type not in valid_types:
            log_type = "repair_action"
        if not note:
            messages.error(request, "Work log note wajib diisi.")
            return redirect("service:service_detail", pk=ticket.pk)

        ServiceWorkLog.objects.create(
            ticket=ticket,
            title=title,
            log_type=log_type,
            technician=technician,
            note=note,
            created_by=request.user if getattr(
                request.user, "is_authenticated", False) else None,
            updated_by=request.user if getattr(
                request.user, "is_authenticated", False) else None,
        )
        messages.success(request, "Work log added.")
        return redirect("service:service_detail", pk=ticket.pk)


class ServiceAddPartView(View):
    def post(self, request, pk):
        ticket = get_object_or_404(
            ServiceTicket.objects.select_related("transaction", "branch"), pk=pk)
        header = ticket.transaction
        if not header:
            messages.error(request, "Ticket belum punya transaksi.")
            return redirect("service:service_detail", pk=ticket.pk)

        qty = _parse_int(request.POST.get(
            "qty") or request.POST.get("part_qty")) or 1
        if qty <= 0:
            qty = 1

        part_id = _parse_int(request.POST.get("part_id"))
        product = None
        if part_id:
            product = Product.objects.filter(pk=part_id).first()

        if not product:
            search = (request.POST.get("part_name_search") or "").strip()
            m = re.search(r"SKU\s*:\s*([^)]+)\)", search)
            if m:
                sku = m.group(1).strip()
                product = Product.objects.filter(sku=sku).first()

        if not product:
            messages.error(request, "Part tidak ditemukan. Pilih dari list.")
            return redirect("service:service_detail", pk=ticket.pk)

        price = _as_decimal(request.POST.get("price") or request.POST.get(
            "part_price"), product.selling_price)
        cost = getattr(product, "base_price", Decimal("0")) or Decimal("0")

        # Stock deduction (only for physical products)
        if product.product_type != "SERVICE":
            stock, _created = Stock.objects.get_or_create(
                product=product, branch=ticket.branch)
            if not stock.reduce_stock(qty):
                messages.error(request, "Stok tidak cukup di cabang ini.")
                return redirect("service:service_detail", pk=ticket.pk)

        TransactionDetail.objects.create(
            header=header,
            product=product,
            related_service_ticket=ticket,
            qty=qty,
            price_at_trx=price,
            cost_at_trx=cost,
        )
        _recalc_header_total(header)

        ServiceWorkLog.objects.create(
            ticket=ticket,
            title="Part Used",
            log_type="part_used",
            technician=ticket.technician,
            note=f"{qty} x {product.name}",
            created_by=request.user if getattr(
                request.user, "is_authenticated", False) else None,
            updated_by=request.user if getattr(
                request.user, "is_authenticated", False) else None,
        )

        messages.success(request, "Part added.")
        return redirect("service:service_detail", pk=ticket.pk)


class ServiceRemovePartView(View):
    def post(self, request, pk, detail_id):
        ticket = get_object_or_404(
            ServiceTicket.objects.select_related("transaction", "branch"), pk=pk)
        header = ticket.transaction
        detail = get_object_or_404(
            TransactionDetail.objects.select_related("product"),
            pk=detail_id,
            header=header,
            related_service_ticket=ticket,
        )

        # Restore stock if physical product
        if detail.product.product_type != "SERVICE":
            stock, _created = Stock.objects.get_or_create(
                product=detail.product, branch=ticket.branch)
            stock.add_stock(detail.qty)

        detail.delete()
        _recalc_header_total(header)
        messages.success(request, "Part removed.")
        return redirect("service:service_detail", pk=ticket.pk)


class ServiceUpdateLaborView(View):
    def post(self, request, pk):
        ticket = get_object_or_404(
            ServiceTicket.objects.select_related("transaction"), pk=pk)
        header = ticket.transaction
        if not header:
            messages.error(request, "Ticket belum punya transaksi.")
            return redirect("service:service_detail", pk=ticket.pk)

        labor_description = (request.POST.get(
            "labor_description") or "").strip()
        labor_fee = _as_decimal(request.POST.get("labor_fee"), Decimal("0"))
        ticket.labor_description = labor_description
        ticket.updated_by = request.user if getattr(
            request.user, "is_authenticated", False) else None
        ticket.save(update_fields=[
                    "labor_description", "updated_by", "updated_at"])

        labor_product = _get_or_create_labor_product()
        cost = getattr(labor_product, "base_price",
                       Decimal("0")) or Decimal("0")

        item = TransactionDetail.objects.filter(
            header=header,
            related_service_ticket=ticket,
            product=labor_product,
        ).first()
        if labor_fee <= 0:
            if item:
                item.delete()
        else:
            if not item:
                TransactionDetail.objects.create(
                    header=header,
                    product=labor_product,
                    related_service_ticket=ticket,
                    qty=1,
                    price_at_trx=labor_fee,
                    cost_at_trx=cost,
                )
            else:
                item.qty = 1
                item.price_at_trx = labor_fee
                item.cost_at_trx = cost
                item.save(update_fields=["qty", "price_at_trx", "cost_at_trx"])

        _recalc_header_total(header)
        messages.success(request, "Labor updated.")
        return redirect("service:service_detail", pk=ticket.pk)


class ServiceAssignTechnicianView(View):
    def post(self, request, pk):
        ticket = get_object_or_404(ServiceTicket, pk=pk)
        technician_id = _parse_int(request.POST.get("technician_id"))
        technician = User.objects.filter(
            pk=technician_id).first() if technician_id else None
        ticket.technician = technician
        ticket.updated_by = request.user if getattr(
            request.user, "is_authenticated", False) else None
        ticket.save(update_fields=["technician", "updated_by", "updated_at"])
        messages.success(request, "Technician assigned.")
        return redirect("service:service_detail", pk=ticket.pk)


class ServiceFinalizeView(View):
    def post(self, request, pk):
        ticket = get_object_or_404(
            ServiceTicket.objects.select_related("transaction"), pk=pk)
        header = ticket.transaction
        if not header:
            messages.error(request, "Ticket belum punya transaksi.")
            return redirect("service:service_billing", pk=ticket.pk)

        action = (request.POST.get("action") or "finalize").strip()
        discount = _as_decimal(request.POST.get(
            "discount"), ticket.discount_amount or Decimal("0"))
        warranty_days = _parse_int(request.POST.get("warranty_days")) or 0
        invoice_notes = (request.POST.get("invoice_notes") or "").strip()

        payment_method_ui = (request.POST.get(
            "payment_method") or "cash").strip().lower()
        is_credit = bool(request.POST.get("is_credit")
                         ) or payment_method_ui == "credit"

        amount_paid = _as_decimal(
            request.POST.get("amount_paid"), Decimal("0"))
        dp_amount = _as_decimal(request.POST.get("dp_amount"), Decimal("0"))
        due_date = _parse_date(request.POST.get("due_date"))

        ticket.discount_amount = discount
        ticket.warranty_days = max(0, warranty_days)
        ticket.invoice_notes = invoice_notes
        ticket.updated_by = request.user if getattr(
            request.user, "is_authenticated", False) else None
        ticket.save(update_fields=[
                    "discount_amount", "warranty_days", "invoice_notes", "updated_by", "updated_at"])

        subtotal = _recalc_header_total(header)
        total_after_discount = subtotal - (discount or Decimal("0"))
        if total_after_discount < 0:
            total_after_discount = Decimal("0")

        header.total_amount = total_after_discount
        header.payment_method = "CREDIT" if is_credit else "CASH"
        header.due_date = due_date if is_credit else None
        header.amount_paid = dp_amount if is_credit else amount_paid
        header.updated_by = request.user if getattr(
            request.user, "is_authenticated", False) else None

        if action == "save_draft":
            header.is_finalized = False
            header.save(update_fields=["total_amount", "payment_method",
                        "amount_paid", "due_date", "is_finalized", "updated_by", "updated_at"])
            messages.success(request, "Billing draft saved.")
            return redirect("service:service_billing", pk=ticket.pk)

        # finalize
        if is_credit and not due_date:
            messages.error(request, "Due date wajib untuk pembayaran credit.")
            return redirect("service:service_billing", pk=ticket.pk)

        header.is_finalized = True
        header.save(update_fields=["total_amount", "payment_method",
                    "amount_paid", "due_date", "is_finalized", "updated_by", "updated_at"])

        # Move ticket to ready for pickup
        ticket.status = "DONE"
        ticket.save(update_fields=["status", "updated_by", "updated_at"])

        ServiceWorkLog.objects.create(
            ticket=ticket,
            title="Finalized & Billed",
            log_type="completed",
            technician=ticket.technician,
            note=f"Invoice {header.invoice_number} finalized. Total {header.total_amount}.",
            created_by=request.user if getattr(
                request.user, "is_authenticated", False) else None,
            updated_by=request.user if getattr(
                request.user, "is_authenticated", False) else None,
        )

        messages.success(request, "Service finalized & billed.")
        return redirect("service:service_queue")
