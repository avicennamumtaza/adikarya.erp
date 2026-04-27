from __future__ import annotations

import csv
import hashlib
from decimal import Decimal
from typing import Any

from django import forms
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse

from .models import Contact


DB_TO_UI_TYPE = {
    "CUSTOMER": "Customer",
    "SUPPLIER": "Supplier",
    "BOTH": "Both",
}

UI_TO_DB_TYPE = {value: key for key, value in DB_TO_UI_TYPE.items()}


class PartnerForm(forms.Form):
    name = forms.CharField(max_length=150, required=True)
    type = forms.ChoiceField(
        choices=[("Customer", "Customer"), ("Supplier", "Supplier"), ("Both", "Both")])
    phone = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=False)
    balance = forms.DecimalField(
        required=False, decimal_places=2, max_digits=15)
    status = forms.ChoiceField(
        choices=[("Active", "Active"), ("Inactive", "Inactive")], required=False)
    address = forms.CharField(required=False)
    notes = forms.CharField(required=False, max_length=50)

    def clean_balance(self) -> Decimal:
        value = self.cleaned_data.get("balance")
        return value if value is not None else Decimal("0")


def _compute_status(contact: Contact) -> str:
    return "Active" if contact.current_balance != 0 else "Inactive"


def _avatar_color_from_name(name: str) -> str:
    palette = [
        "#1e293b",
        "#0f766e",
        "#1d4ed8",
        "#9333ea",
        "#be123c",
        "#0369a1",
        "#166534",
        "#b45309",
    ]
    if not name:
        return palette[0]
    digest = hashlib.md5(name.encode("utf-8")).digest()[0]
    return palette[digest % len(palette)]


def apply_filters(base_qs, query_params):
    qs = base_qs

    keyword = (query_params.get("q") or "").strip()
    if keyword:
        qs = qs.filter(
            Q(name__icontains=keyword)
            | Q(email__icontains=keyword)
            | Q(whatsapp__icontains=keyword)
            | Q(address__icontains=keyword)
        )

    ui_type = (query_params.get("type") or "").strip()
    db_type = UI_TO_DB_TYPE.get(ui_type)
    if db_type:
        qs = qs.filter(contact_type=db_type)

    status = (query_params.get("status") or "").strip()
    if status == "Active":
        qs = qs.exclude(current_balance=0)
    elif status == "Inactive":
        qs = qs.filter(current_balance=0)

    return qs


def attach_ui_fields(contact: Contact) -> Contact:
    contact.type = DB_TO_UI_TYPE.get(contact.contact_type, "Both")
    contact.phone = contact.whatsapp
    contact.balance = contact.current_balance
    contact.status = _compute_status(contact)
    contact.notes = contact.instagram or ""
    contact.avatar_color = _avatar_color_from_name(contact.name)
    return contact


def paginate_contacts(qs, page_number: str, per_page: int = 10):
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page_number)
    for contact in page_obj.object_list:
        attach_ui_fields(contact)
    return page_obj


def partner_stats() -> dict[str, Any]:
    base_qs = Contact.objects.all()
    receivable = base_qs.filter(current_balance__gt=0).aggregate(
        total=Coalesce(Sum("current_balance"), Decimal("0"))
    )["total"]
    payable = base_qs.filter(current_balance__lt=0).aggregate(
        total=Coalesce(Sum("current_balance"), Decimal("0"))
    )["total"]

    return {
        "stat_total": base_qs.count(),
        "stat_receivable": int(receivable),
        "stat_payable": int(abs(payable)),
        "stat_active": base_qs.exclude(current_balance=0).count(),
    }


def initialize_form(contact: Contact | None = None) -> PartnerForm:
    if contact is None:
        return PartnerForm(initial={"status": "Active"})

    return PartnerForm(
        initial={
            "name": contact.name,
            "type": DB_TO_UI_TYPE.get(contact.contact_type, "Both"),
            "phone": contact.whatsapp,
            "email": contact.email,
            "balance": contact.current_balance,
            "status": _compute_status(contact),
            "address": contact.address,
            "notes": contact.instagram or "",
        }
    )


def save_form(form: PartnerForm, contact: Contact | None = None) -> Contact:
    instance = contact or Contact()
    instance.name = form.cleaned_data["name"]
    instance.contact_type = UI_TO_DB_TYPE[form.cleaned_data["type"]]
    instance.whatsapp = form.cleaned_data["phone"]
    instance.email = form.cleaned_data.get("email") or None
    instance.current_balance = form.cleaned_data.get("balance") or Decimal("0")
    instance.address = form.cleaned_data.get("address") or ""
    # Reuse optional social field as short internal note until a dedicated column exists.
    instance.instagram = form.cleaned_data.get("notes") or None
    instance.save()
    return attach_ui_fields(instance)


def build_export_response(qs) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="partners.csv"'

    writer = csv.writer(response)
    writer.writerow(["Name", "Type", "Phone", "Email",
                    "Address", "Balance", "Status"])

    for contact in qs:
        attach_ui_fields(contact)
        writer.writerow(
            [
                contact.name,
                contact.type,
                contact.phone,
                contact.email or "",
                contact.address,
                contact.balance,
                contact.status,
            ]
        )

    return response
