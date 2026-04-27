from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django import forms
from django.core.paginator import Paginator
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse

from .models import Branch, Product, Stock


DB_TO_UI_PRODUCT_TYPE = {
    "PRODUCT": "Goods",
    "SERVICE": "Service",
}

UI_TO_DB_PRODUCT_TYPE = {value: key for key,
                         value in DB_TO_UI_PRODUCT_TYPE.items()}

DEFAULT_CATEGORIES = ["Electronics", "Clothing",
                      "Food & Beverage", "Stationery", "Home Goods"]


class ProductForm(forms.Form):
    name = forms.CharField(max_length=200, required=True)
    sku = forms.CharField(max_length=50, required=True)
    category = forms.CharField(required=True)
    brand = forms.CharField(required=False, max_length=100)
    product_type = forms.ChoiceField(
        choices=[("Goods", "Goods"), ("Service", "Service")])
    notes = forms.CharField(required=False)
    sell_price = forms.DecimalField(
        required=True, decimal_places=2, max_digits=12)
    min_stock = forms.IntegerField(required=True, min_value=0)
    init_stock = forms.IntegerField(required=False, min_value=0)
    branch_assign = forms.IntegerField(required=False)

    def clean_sell_price(self) -> Decimal:
        value = self.cleaned_data["sell_price"]
        if value <= 0:
            raise forms.ValidationError(
                "Selling price must be greater than 0.")
        return value


class BranchForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    address = forms.CharField(required=True)
    manager = forms.CharField(required=False, max_length=100)
    phone = forms.CharField(required=False, max_length=30)
    email = forms.EmailField(required=False)
    status = forms.ChoiceField(
        choices=[("active", "Active"), ("inactive", "Inactive")], required=False)


@dataclass
class ProductDetailSummary:
    total_units: int
    low_branches: int
    out_branches: int
    min_total: int
    progress_pct: int


def _safe_pct(stock: int, min_stock: int) -> int:
    if min_stock <= 0:
        return 100 if stock > 0 else 0
    pct = int((stock / max(min_stock * 2, 1)) * 100)
    return max(0, min(100, pct))


def _derive_category(product: Product) -> str:
    return "Electronics" if product.product_type == "PRODUCT" else "Services"


def _derive_brand(product: Product) -> str:
    return "Generic"


def _derive_emoji(product: Product) -> str:
    return "📦" if product.product_type == "PRODUCT" else "🛠️"


def _derive_status(product: Product) -> str:
    return "Active" if product.total_stock > 0 else "Inactive"


def attach_product_ui_fields(product: Product) -> Product:
    product.stock = int(getattr(product, "total_stock", 0) or 0)
    product.sell_price = product.selling_price
    product.type = DB_TO_UI_PRODUCT_TYPE.get(product.product_type, "Goods")
    product.category = _derive_category(product)
    product.brand = _derive_brand(product)
    product.emoji = _derive_emoji(product)
    product.status = _derive_status(product)
    product.notes = ""

    if product.base_price and product.selling_price:
        margin = ((product.selling_price - product.base_price) /
                  product.base_price) * 100 if product.base_price > 0 else Decimal("0")
        product.margin = f"{margin:.1f}%"
    else:
        product.margin = "-"

    product.stock_pct = _safe_pct(product.stock, product.min_stock)
    return product


def product_queryset_with_stock():
    return Product.objects.annotate(total_stock=Coalesce(Sum("branch_stocks__quantity"), 0))


def apply_product_filters(base_qs, query_params):
    qs = base_qs
    keyword = (query_params.get("q") or "").strip()
    if keyword:
        qs = qs.filter(Q(name__icontains=keyword) | Q(sku__icontains=keyword))

    category = (query_params.get("category") or "").strip()
    if category == "Electronics":
        qs = qs.filter(product_type="PRODUCT")
    elif category == "Services":
        qs = qs.filter(product_type="SERVICE")

    stock_status = (query_params.get("stock_status") or "").strip()
    if stock_status == "out":
        qs = qs.filter(total_stock=0)
    elif stock_status == "low":
        qs = qs.filter(total_stock__gt=0, total_stock__lte=F("min_stock"))
    elif stock_status == "ok":
        qs = qs.filter(total_stock__gt=F("min_stock"))

    return qs


def paginate_products(qs, page_number: str, per_page: int = 10):
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page_number)
    for product in page_obj.object_list:
        attach_product_ui_fields(product)
    return page_obj


def product_stats() -> dict[str, Any]:
    qs = product_queryset_with_stock()
    products = list(qs)

    stat_skus = len(products)
    stat_low = 0
    stat_out = 0
    stat_value = Decimal("0")
    for product in products:
        stock = int(product.total_stock or 0)
        if stock == 0:
            stat_out += 1
        elif stock <= product.min_stock:
            stat_low += 1
        stat_value += (product.base_price or Decimal("0")) * stock

    return {
        "stat_skus": stat_skus,
        "stat_low": stat_low,
        "stat_out": stat_out,
        "stat_value": int(stat_value),
    }


def initialize_product_form(product: Product | None = None) -> ProductForm:
    if product is None:
        return ProductForm(initial={"product_type": "Goods", "min_stock": 10, "init_stock": 0})

    return ProductForm(
        initial={
            "name": product.name,
            "sku": product.sku,
            "category": _derive_category(product),
            "brand": _derive_brand(product),
            "product_type": DB_TO_UI_PRODUCT_TYPE.get(product.product_type, "Goods"),
            "notes": "",
            "sell_price": product.selling_price,
            "min_stock": product.min_stock,
        }
    )


def save_product_form(form: ProductForm, product: Product | None = None) -> Product:
    instance = product or Product()
    instance.name = form.cleaned_data["name"]
    instance.sku = form.cleaned_data["sku"]
    instance.product_type = UI_TO_DB_PRODUCT_TYPE[form.cleaned_data["product_type"]]
    instance.selling_price = form.cleaned_data["sell_price"]
    instance.min_stock = form.cleaned_data["min_stock"]
    instance.save()

    init_stock = form.cleaned_data.get("init_stock")
    branch_id = form.cleaned_data.get("branch_assign")
    if product is None and init_stock and init_stock > 0 and branch_id:
        branch = Branch.objects.filter(pk=branch_id).first()
        if branch:
            stock, _ = Stock.objects.get_or_create(
                product=instance, branch=branch, defaults={"quantity": 0})
            stock.quantity = int(stock.quantity or 0) + init_stock
            stock.save(update_fields=["quantity", "updated_at"])

    return attach_product_ui_fields(instance)


def build_product_export_response(qs) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="products.csv"'
    writer = csv.writer(response)
    writer.writerow(["Name", "SKU", "Category", "Type", "Base Price",
                    "Sell Price", "Stock", "Min Stock", "Status"])

    for product in qs:
        attach_product_ui_fields(product)
        writer.writerow(
            [
                product.name,
                product.sku,
                product.category,
                product.type,
                product.base_price,
                product.sell_price,
                product.stock,
                product.min_stock,
                "Out" if product.stock == 0 else (
                    "Low" if product.stock <= product.min_stock else "In Stock"),
            ]
        )

    return response


def branch_stats() -> dict[str, Any]:
    branches = list(Branch.objects.all())
    total_branches = len(branches)
    total_skus = Product.objects.count()

    low_branches = 0
    for branch in branches:
        has_low = branch.stock_levels.filter(
            quantity__gt=0,
            quantity__lte=F("product__min_stock"),
        ).exists()
        if has_low:
            low_branches += 1

    all_stocks = Stock.objects.aggregate(
        total=Coalesce(Sum("quantity"), 0))["total"]
    avg = int(all_stocks / total_skus) if total_skus else 0

    return {
        "stat_branches": total_branches,
        "stat_skus": total_skus,
        "stat_low_branches": low_branches,
        "stat_avg": avg,
    }


def initialize_branch_form(branch: Branch | None = None) -> BranchForm:
    if branch is None:
        return BranchForm(initial={"status": "active"})

    return BranchForm(
        initial={
            "name": branch.name,
            "address": branch.address,
            "manager": "",
            "phone": "",
            "email": "",
            "status": "active" if branch.is_active else "inactive",
        }
    )


def save_branch_form(form: BranchForm, branch: Branch | None = None) -> Branch:
    instance = branch or Branch()
    instance.name = form.cleaned_data["name"]
    instance.address = form.cleaned_data["address"]
    instance.is_active = form.cleaned_data.get(
        "status", "active") != "inactive"
    instance.save()

    instance.manager = form.cleaned_data.get("manager", "")
    instance.phone = form.cleaned_data.get("phone", "")
    instance.email = form.cleaned_data.get("email", "")
    instance.status = "active" if instance.is_active else "inactive"
    return instance


def enrich_branches_for_ui(branches):
    for branch in branches:
        branch.manager = ""
        branch.phone = ""
        branch.email = ""
        branch.status = "active" if branch.is_active else "inactive"
        branch.sku_count = branch.stock_levels.values(
            "product").distinct().count()
    return branches


def get_product_branch_stocks(product: Product):
    branch_stocks = list(
        Stock.objects.filter(product=product)
        .select_related("branch")
        .order_by("branch__name")
    )

    total_units = 0
    low_branches = 0
    out_branches = 0
    for stock in branch_stocks:
        qty = int(stock.quantity or 0)
        total_units += qty
        if qty == 0:
            out_branches += 1
        elif qty <= product.min_stock:
            low_branches += 1

        stock.min_stock = product.min_stock
        stock.status = "Out" if qty == 0 else (
            "Low" if qty <= product.min_stock else "In Stock")

    min_total = product.min_stock * max(len(branch_stocks), 1)
    progress_pct = _safe_pct(total_units, min_total)

    return branch_stocks, ProductDetailSummary(
        total_units=total_units,
        low_branches=low_branches,
        out_branches=out_branches,
        min_total=min_total,
        progress_pct=progress_pct,
    )
