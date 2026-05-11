from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Prefetch
from django.views import View

from .models import Branch, Product, Stock
from .services import (
    BranchForm,
    DEFAULT_CATEGORIES,
    ProductForm,
    apply_product_filters,
    branch_stats,
    build_product_export_response,
    enrich_branches_for_ui,
    get_product_branch_stocks,
    initialize_branch_form,
    initialize_product_form,
    paginate_products,
    product_categories,
    product_queryset_with_stock,
    product_stats,
    save_branch_form,
    save_product_form,
    attach_product_ui_fields,
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


class ProductListView(View):
    template_name = "product/product_list.html"

    def get(self, request):
        queryset = product_queryset_with_stock().order_by("name")
        filtered = apply_product_filters(queryset, request.GET)
        products = paginate_products(
            filtered, request.GET.get("page"), per_page=10)
        for product in products.object_list:
            _normalize_money_fields(product, ("base_price", "sell_price"))

        context = {
            "products": products,
            "categories": product_categories(),
            **product_stats(),
        }
        return render(request, self.template_name, context)


class ProductCreateView(View):
    template_name = "product/product_form.html"

    def get(self, request):
        context = {
            "form": initialize_product_form(),
            "product": None,
            "categories": product_categories(),
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = ProductForm(request.POST)
        if form.is_valid():
            sku = (form.cleaned_data.get("sku") or "").strip()
            if sku and Product.objects.filter(sku=sku).exists():
                form.add_error(
                    "sku", "SKU sudah digunakan. Gunakan SKU yang unik.")
            else:
                save_product_form(form)
                messages.success(request, "Product berhasil ditambahkan.")
                return redirect("product_list")

        context = {
            "form": form,
            "product": None,
            "categories": product_categories(),
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
        }
        return render(request, self.template_name, context)


class ProductUpdateView(View):
    template_name = "product/product_form.html"

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        attach_product_ui_fields(product)
        context = {
            "form": initialize_product_form(product),
            "product": product,
            "categories": product_categories(),
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(request.POST)
        if form.is_valid():
            sku = (form.cleaned_data.get("sku") or "").strip()
            if sku and Product.objects.filter(sku=sku).exclude(pk=product.pk).exists():
                form.add_error(
                    "sku", "SKU sudah digunakan. Gunakan SKU yang unik.")
            else:
                save_product_form(form, product=product)
                messages.success(request, "Product berhasil diperbarui.")
                return redirect("product_list")

        attach_product_ui_fields(product)
        context = {
            "form": form,
            "product": product,
            "categories": product_categories(),
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
        }
        return render(request, self.template_name, context)


class ProductDetailView(View):
    template_name = "product/product_detail.html"

    def get(self, request, pk):
        product = get_object_or_404(product_queryset_with_stock(), pk=pk)
        attach_product_ui_fields(product)
        _normalize_money_fields(product, ("base_price", "sell_price"))
        branch_stocks, summary = get_product_branch_stocks(product)

        context = {
            "product": product,
            "branch_stocks": branch_stocks,
            "detail_summary": summary,
        }
        return render(request, self.template_name, context)


class ProductDeleteView(View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        messages.success(request, "Product berhasil dihapus.")
        return redirect("product_list")

    def get(self, request, pk):
        return self.post(request, pk)


class ProductExportView(View):
    def get(self, request):
        queryset = product_queryset_with_stock().order_by("name")
        filtered = apply_product_filters(queryset, request.GET)
        return build_product_export_response(filtered)


class ProductStockAdjustView(View):
    template_name = "product/product_stock_adjust.html"

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        attach_product_ui_fields(product)

        if product.product_type == "SERVICE":
            messages.info(
                request, "Service tidak memiliki stok untuk disesuaikan.")
            return redirect("product_detail", pk=pk)

        branches = Branch.objects.filter(is_active=True).order_by("name")
        selected_branch_id = (request.GET.get("branch") or "").strip()
        current_qty = 0

        if selected_branch_id:
            stock = Stock.objects.filter(
                product=product, branch_id=selected_branch_id).first()
            current_qty = int(getattr(stock, "quantity", 0) or 0)

        context = {
            "product": product,
            "branches": branches,
            "selected_branch_id": selected_branch_id,
            "current_qty": current_qty,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        if product.product_type == "SERVICE":
            messages.info(
                request, "Service tidak memiliki stok untuk disesuaikan.")
            return redirect("product_detail", pk=pk)

        branch_id = request.POST.get("branch") or request.GET.get("branch")
        qty = request.POST.get("qty")

        if not branch_id or qty is None:
            messages.error(request, "Parameter branch dan qty wajib diisi.")
            return redirect("product_stock_adjust", pk=pk)

        try:
            qty_int = int(qty)
        except (TypeError, ValueError):
            messages.error(request, "Qty harus berupa angka.")
            return redirect("product_stock_adjust", pk=pk)

        if qty_int < 0:
            messages.error(request, "Qty tidak boleh negatif.")
            return redirect("product_stock_adjust", pk=pk)

        branch = get_object_or_404(Branch, pk=branch_id, is_active=True)
        stock, _ = Stock.objects.get_or_create(
            product=product, branch=branch, defaults={"quantity": 0})
        stock.quantity = qty_int
        stock.save(update_fields=["quantity", "updated_at"])
        messages.success(request, "Stok berhasil disesuaikan.")
        return redirect("product_detail", pk=pk)


class BranchListView(View):
    template_name = "branch/branch_list.html"

    def get(self, request):
        branches = enrich_branches_for_ui(
            Branch.objects.all()
            .order_by("name")
            .prefetch_related(Prefetch("stock_levels", queryset=Stock.objects.select_related("product")))
        )
        context = {
            "branches": branches,
            **branch_stats(),
        }
        return render(request, self.template_name, context)


class BranchCreateView(View):
    template_name = "branch/branch_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": initialize_branch_form(), "branch": None})

    def post(self, request):
        form = BranchForm(request.POST)
        if form.is_valid():
            save_branch_form(form)
            messages.success(request, "Branch berhasil ditambahkan.")
            return redirect("branch_list")
        return render(request, self.template_name, {"form": form, "branch": None})


class BranchUpdateView(View):
    template_name = "branch/branch_form.html"

    def get(self, request, pk):
        branch = get_object_or_404(Branch, pk=pk)
        branch.status = "active" if branch.is_active else "inactive"
        form = initialize_branch_form(branch)
        return render(request, self.template_name, {"form": form, "branch": branch})

    def post(self, request, pk):
        branch = get_object_or_404(Branch, pk=pk)
        form = BranchForm(request.POST)
        if form.is_valid():
            save_branch_form(form, branch=branch)
            messages.success(request, "Branch berhasil diperbarui.")
            return redirect("branch_list")

        branch.status = "active" if branch.is_active else "inactive"
        return render(request, self.template_name, {"form": form, "branch": branch})


class BranchDetailView(View):
    def get(self, request, pk):
        return redirect("branch_edit", pk=pk)


class BranchDeleteView(View):
    def post(self, request, pk):
        branch = get_object_or_404(Branch, pk=pk)
        branch.delete()
        messages.success(request, "Branch berhasil dihapus.")
        return redirect("branch_list")

    def get(self, request, pk):
        return self.post(request, pk)
