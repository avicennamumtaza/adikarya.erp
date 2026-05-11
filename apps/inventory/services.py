from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
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


def product_categories() -> list[str]:
    db_categories = list(
        Product.objects.exclude(category="")
        .values_list("category", flat=True)
        .distinct()
    )
    merged = {c for c in (DEFAULT_CATEGORIES + db_categories)
              if (c or "").strip()}
    return sorted(merged)


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
    manager = forms.CharField(required=True, max_length=100)
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
    stored = (getattr(product, "category", "") or "").strip()
    if stored:
        return stored
    return "Electronics" if product.product_type == "PRODUCT" else "Services"


def _derive_brand(product: Product) -> str:
    stored = (getattr(product, "brand", "") or "").strip()
    return stored or "Generic"


def _derive_emoji(product: Product) -> str:
    return "📦" if product.product_type == "PRODUCT" else "🛠️"


def _derive_status(product: Product) -> str:
    # Use annotated value if present, otherwise property
    stock = getattr(product, "total_stock_count", product.total_stock)
    return "Active" if stock > 0 else "Inactive"


def attach_product_ui_fields(product: Product) -> Product:
    product.stock = int(
        getattr(product, "total_stock_count", product.total_stock) or 0)
    product.sell_price = product.selling_price
    product.type = DB_TO_UI_PRODUCT_TYPE.get(product.product_type, "Goods")
    product.category = _derive_category(product)
    product.brand = _derive_brand(product)
    product.emoji = _derive_emoji(product)
    product.status = _derive_status(product)
    product.notes = getattr(product, "notes", "") or ""

    if product.base_price and product.selling_price:
        margin = ((product.selling_price - product.base_price) /
                  product.base_price) * 100 if product.base_price > 0 else Decimal("0")
        product.margin = f"{margin:.1f}%"
    else:
        product.margin = "-"

    product.stock_pct = _safe_pct(product.stock, product.min_stock)
    return product


def product_queryset_with_stock():
    return Product.objects.annotate(total_stock_count=Coalesce(Sum("branch_stocks__quantity"), 0))


def apply_product_filters(base_qs, query_params):
    qs = base_qs
    keyword = (query_params.get("q") or "").strip()
    if keyword:
        qs = qs.filter(Q(name__icontains=keyword) | Q(sku__icontains=keyword))

    category = (query_params.get("category") or "").strip()
    if category:
        qs = qs.filter(category=category)

    stock_status = (query_params.get("stock_status") or "").strip()
    if stock_status == "out":
        qs = qs.filter(total_stock_count=0)
    elif stock_status == "low":
        qs = qs.filter(total_stock_count__gt=0,
                       total_stock_count__lte=F("min_stock"))
    elif stock_status == "ok":
        qs = qs.filter(total_stock_count__gt=F("min_stock"))

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
        stock = int(getattr(product, "total_stock_count",
                    product.total_stock) or 0)
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
        return ProductForm(
            initial={
                "product_type": "Goods",
                "min_stock": 10,
                "init_stock": 0,
                "category": "",
                "brand": "",
                "notes": "",
            }
        )

    return ProductForm(
        initial={
            "name": product.name,
            "sku": product.sku,
            "category": _derive_category(product),
            "brand": _derive_brand(product),
            "product_type": DB_TO_UI_PRODUCT_TYPE.get(product.product_type, "Goods"),
            "notes": getattr(product, "notes", "") or "",
            "sell_price": product.selling_price,
            "min_stock": product.min_stock,
        }
    )


def save_product_form(form: ProductForm, product: Product | None = None) -> Product:
    instance = product or Product()
    instance.name = form.cleaned_data["name"]
    instance.sku = form.cleaned_data["sku"]
    instance.product_type = UI_TO_DB_PRODUCT_TYPE[form.cleaned_data["product_type"]]
    instance.category = form.cleaned_data.get("category", "")
    instance.brand = form.cleaned_data.get("brand", "")
    instance.notes = form.cleaned_data.get("notes", "")
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
            "manager": branch.manager,
            "phone": branch.phone,
            "email": branch.email,
            "status": "active" if branch.is_active else "inactive",
        }
    )


def save_branch_form(form: BranchForm, branch: Branch | None = None) -> Branch:
    instance = branch or Branch()
    instance.name = form.cleaned_data["name"]
    instance.address = form.cleaned_data["address"]
    instance.manager = form.cleaned_data.get("manager", "")
    instance.phone = form.cleaned_data.get("phone", "")
    instance.email = form.cleaned_data.get("email", "")
    instance.is_active = form.cleaned_data.get(
        "status", "active") != "inactive"
    instance.save()

    instance.status = "active" if instance.is_active else "inactive"
    return instance


def enrich_branches_for_ui(branches):
    for branch in branches:
        branch.status = "active" if branch.is_active else "inactive"

        name_parts = [p for p in (branch.name or "").strip().split() if p]
        initials = "".join([p[0].upper() for p in name_parts[:2]])
        branch.initials = initials or (
            branch.name[:2].upper() if branch.name else "BR")

        stocks = list(branch.stock_levels.all())

        product_ids = set()
        low_product_ids = set()
        for stock in stocks:
            product_id = getattr(stock, "product_id", None)
            if product_id is None:
                continue
            product_ids.add(product_id)

            qty = int(stock.quantity or 0)
            min_stock = int(
                getattr(getattr(stock, "product", None), "min_stock", 0) or 0)
            if qty > 0 and qty <= min_stock:
                low_product_ids.add(product_id)

        branch.sku_count = len(product_ids)
        branch.low_skus_count = len(low_product_ids)
    return branches


def get_product_branch_stocks(product: Product):
    branches = list(Branch.objects.filter(is_active=True).order_by("name"))
    existing_stocks = list(
        Stock.objects.filter(product=product, branch__in=branches)
        .select_related("branch")
    )
    stock_by_branch_id = {s.branch_id: s for s in existing_stocks}

    @dataclass
    class ProductBranchStockRow:
        branch: Branch
        quantity: int
        min_stock: int
        status: str
        last_restock_at: datetime | None

    total_units = 0
    low_branches = 0
    out_branches = 0
    rows: list[ProductBranchStockRow] = []
    for branch in branches:
        stock = stock_by_branch_id.get(branch.id)
        qty = int(getattr(stock, "quantity", 0) or 0)
        total_units += qty

        if qty == 0:
            out_branches += 1
            status = "Out of Stock"
        elif qty <= product.min_stock:
            low_branches += 1
            status = "Low Stock"
        else:
            status = "In Stock"

        rows.append(
            ProductBranchStockRow(
                branch=branch,
                quantity=qty,
                min_stock=int(product.min_stock or 0),
                status=status,
                last_restock_at=getattr(stock, "updated_at", None),
            )
        )

    min_total = int(product.min_stock or 0) * max(len(branches), 1)
    progress_pct = _safe_pct(total_units, min_total)

    return rows, ProductDetailSummary(
        total_units=total_units,
        low_branches=low_branches,
        out_branches=out_branches,
        min_total=min_total,
        progress_pct=progress_pct,
    )
