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


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
            "name",
            "contact_type",
            "whatsapp",
            "instagram",
            "facebook",
            "email",
            "address",
            "current_balance",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-input"})
            field.required = False
        
        self.fields["name"].required = True
        self.fields["contact_type"].required = True
        self.fields["whatsapp"].required = True


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

    contact_type = (query_params.get("type") or "").strip()
    if contact_type:
        qs = qs.filter(contact_type=contact_type)

    status = (query_params.get("status") or "").strip()
    if status == "Active":
        qs = qs.exclude(current_balance=0)
    elif status == "Inactive":
        qs = qs.filter(current_balance=0)

    return qs


def attach_ui_fields(contact: Contact) -> Contact:
    contact.status_label = _compute_status(contact)
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


def save_form(form: PartnerForm) -> Contact:
    instance = form.save()
    return attach_ui_fields(instance)


def build_export_response(qs) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="partners.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ["Name", "Type", "WhatsApp", "Email", "Address", "Balance", "Status"]
    )

    for contact in qs:
        status = _compute_status(contact)
        writer.writerow(
            [
                contact.name,
                contact.get_contact_type_display(),
                contact.whatsapp,
                contact.email or "",
                contact.address,
                contact.current_balance,
                status,
            ]
        )

    return response
