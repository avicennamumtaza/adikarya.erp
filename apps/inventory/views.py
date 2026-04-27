from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
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
    product_queryset_with_stock,
    product_stats,
    save_branch_form,
    save_product_form,
    attach_product_ui_fields,
)


class ProductListView(View):
    template_name = "product/product_list.html"

    def get(self, request):
        queryset = product_queryset_with_stock().order_by("name")
        filtered = apply_product_filters(queryset, request.GET)
        products = paginate_products(
            filtered, request.GET.get("page"), per_page=10)

        context = {
            "products": products,
            "categories": DEFAULT_CATEGORIES,
            **product_stats(),
        }
        return render(request, self.template_name, context)


class ProductCreateView(View):
    template_name = "product/product_form.html"

    def get(self, request):
        context = {
            "form": initialize_product_form(),
            "product": None,
            "categories": DEFAULT_CATEGORIES,
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = ProductForm(request.POST)
        if form.is_valid():
            save_product_form(form)
            messages.success(request, "Product berhasil ditambahkan.")
            return redirect("product_list")

        context = {
            "form": form,
            "product": None,
            "categories": DEFAULT_CATEGORIES,
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
            "categories": DEFAULT_CATEGORIES,
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(request.POST)
        if form.is_valid():
            save_product_form(form, product=product)
            messages.success(request, "Product berhasil diperbarui.")
            return redirect("product_list")

        attach_product_ui_fields(product)
        context = {
            "form": form,
            "product": product,
            "categories": DEFAULT_CATEGORIES,
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
        }
        return render(request, self.template_name, context)


class ProductDetailView(View):
    template_name = "product/product_detail.html"

    def get(self, request, pk):
        product = get_object_or_404(product_queryset_with_stock(), pk=pk)
        attach_product_ui_fields(product)
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
    def get(self, request, pk):
        messages.info(
            request, "Gunakan endpoint ini via POST untuk melakukan penyesuaian stok.")
        return redirect("product_detail", pk=pk)

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        branch_id = request.POST.get("branch") or request.GET.get("branch")
        qty = request.POST.get("qty")

        if not branch_id or qty is None:
            messages.error(request, "Parameter branch dan qty wajib diisi.")
            return redirect("product_detail", pk=pk)

        branch = get_object_or_404(Branch, pk=branch_id)
        stock, _ = Stock.objects.get_or_create(
            product=product, branch=branch, defaults={"quantity": 0})
        stock.quantity = int(qty)
        stock.save(update_fields=["quantity", "updated_at"])
        messages.success(request, "Stok berhasil disesuaikan.")
        return redirect("product_detail", pk=pk)


class BranchListView(View):
    template_name = "branch/branch_list.html"

    def get(self, request):
        branches = enrich_branches_for_ui(
            Branch.objects.all().order_by("name"))
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
        branch.manager = ""
        branch.phone = ""
        branch.email = ""
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
