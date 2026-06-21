from django.urls import path

from .views import (
    ServiceBillingView,
    ServiceFinalizeView,
    ServiceCheckinEditView,
    ServiceCheckinSaveView,
    ServiceCheckinView,
    ServiceDetailView,
    ServiceExportView,
    ServicePrintTagView,
    ServiceQueueView,
    ServiceIntakeUsbPrintView,
    ServiceInvoiceUsbPrintView,
    ServiceUpdateStatusView,
)

app_name = "service"

urlpatterns = [
    path("queue/", ServiceQueueView.as_view(), name="service_queue"),
    path("checkin/", ServiceCheckinView.as_view(), name="service_checkin"),
    path("checkin/save/", ServiceCheckinSaveView.as_view(),
         name="service_checkin_save"),
    path("export/", ServiceExportView.as_view(), name="service_export"),
    path("detail/<int:pk>/", ServiceDetailView.as_view(), name="service_detail"),
    path(
        "detail/<int:pk>/update-status/",
        ServiceUpdateStatusView.as_view(),
        name="service_update_status",
    ),
    path("checkin/<int:pk>/edit/", ServiceCheckinEditView.as_view(),
         name="service_checkin_edit"),
    # path("print-tag/<int:pk>/", ServicePrintTagView.as_view(),
    #      name="service_print_tag"),
    path("print-usb/<int:pk>/", ServiceIntakeUsbPrintView.as_view(),
         name="service_receipt_usb_print"),
    path("billing/<int:pk>/", ServiceBillingView.as_view(), name="service_billing"),
    path(
        "billing/<int:pk>/finalize/",
        ServiceFinalizeView.as_view(),
        name="service_finalize",
    ),
    path(
        "billing/<int:pk>/usb-print/",
        ServiceInvoiceUsbPrintView.as_view(),
        name="service_invoice_usb_print",
    ),
]
