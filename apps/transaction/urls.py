from django.urls import path

from .views import (
    PurchaseCreateView,
    PurchaseDetailView,
    PurchaseExportView,
    PurchaseListView,
    PurchasePayView,
    PurchasePayablesExportView,
    PurchasePayablesView,
    PurchasePrintView,
    PurchaseUsbPrintView,
    SalesCreateView,
    SalesDetailView,
    SalesExportView,
    SalesListView,
    SalesPayView,
    SalesPrintView,
    SalesUsbPrintView,
    SalesReceivablesView,
)

app_name = "transaction"

urlpatterns = [
    path("purchase/", PurchaseListView.as_view(), name="purchase_list"),
    path("purchase/add/", PurchaseCreateView.as_view(), name="purchase_create"),
    path("purchase/export/", PurchaseExportView.as_view(), name="purchase_export"),
    path("purchase/payables/", PurchasePayablesView.as_view(),
         name="purchase_payables"),
    path(
        "purchase/payables/export/",
        PurchasePayablesExportView.as_view(),
        name="purchase_payables_export",
    ),
    path("purchase/pay/", PurchasePayView.as_view(), name="purchase_pay"),
    path("purchase/<int:pk>/", PurchaseDetailView.as_view(), name="purchase_detail"),
    path("purchase/<int:pk>/print/",
         PurchasePrintView.as_view(), name="purchase_print"),
    path("purchase/<int:pk>/usb-print/",
         PurchaseUsbPrintView.as_view(), name="purchase_usb_print"),
    path("sales/", SalesListView.as_view(), name="sales_list"),
    path("sales/pos/", SalesCreateView.as_view(), name="sales_pos"),
    path("sales/export/", SalesExportView.as_view(), name="sales_export"),
    path("sales/receivables/", SalesReceivablesView.as_view(),
         name="sales_receivables"),
    path("sales/pay/", SalesPayView.as_view(), name="sales_pay"),
    path("sales/<int:pk>/", SalesDetailView.as_view(), name="sales_detail"),
    path("sales/<int:pk>/print/", SalesPrintView.as_view(), name="sales_print"),
    path("sales/<int:pk>/usb-print/",
         SalesUsbPrintView.as_view(), name="sales_usb_print"),
]
