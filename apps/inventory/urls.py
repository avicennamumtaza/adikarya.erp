from django.urls import path

from .views import (
    BranchCreateView,
    BranchDeleteView,
    BranchDetailView,
    BranchListView,
    BranchUpdateView,
    ProductCreateView,
    ProductDeleteView,
    ProductDetailView,
    ProductExportView,
    ProductListView,
    ProductStockAdjustView,
    ProductUpdateView,
)

urlpatterns = [
    path("", ProductListView.as_view(), name="product_list"),
    path("products/add/", ProductCreateView.as_view(), name="product_add"),
    path("products/export/", ProductExportView.as_view(), name="product_export"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("products/<int:pk>/edit/",
         ProductUpdateView.as_view(), name="product_edit"),
    path("products/<int:pk>/delete/",
         ProductDeleteView.as_view(), name="product_delete"),
    path("products/<int:pk>/stock-adjust/",
         ProductStockAdjustView.as_view(), name="product_stock_adjust"),
    path("branches/", BranchListView.as_view(), name="branch_list"),
    path("branches/add/", BranchCreateView.as_view(), name="branch_add"),
    path("branches/<int:pk>/", BranchDetailView.as_view(), name="branch_detail"),
    path("branches/<int:pk>/edit/", BranchUpdateView.as_view(), name="branch_edit"),
    path("branches/<int:pk>/delete/",
         BranchDeleteView.as_view(), name="branch_delete"),
]
