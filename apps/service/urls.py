from django.urls import path

from .views import (
    ServiceBillingView,
    ServiceFinalizeView,
    ServiceAddLogView,
    ServiceAddPartView,
    ServiceCheckinEditView,
    ServiceCheckinSaveView,
    ServiceCheckinView,
    ServiceDetailView,
    ServiceExportView,
    ServicePrintTagView,
    ServiceQueueView,
    ServiceUpdateLaborView,
    ServiceUpdateStatusView,
    ServiceAssignTechnicianView,
    ServiceRemovePartView,
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
    path(
        "detail/<int:pk>/add-log/",
        ServiceAddLogView.as_view(),
        name="service_add_log",
    ),
    path(
        "detail/<int:pk>/add-part/",
        ServiceAddPartView.as_view(),
        name="service_add_part",
    ),
    path(
        "detail/<int:pk>/remove-part/<int:detail_id>/",
        ServiceRemovePartView.as_view(),
        name="service_remove_part",
    ),
    path(
        "detail/<int:pk>/update-labor/",
        ServiceUpdateLaborView.as_view(),
        name="service_update_labor",
    ),
    path(
        "detail/<int:pk>/assign-technician/",
        ServiceAssignTechnicianView.as_view(),
        name="service_assign_technician",
    ),
    path("checkin/<int:pk>/edit/", ServiceCheckinEditView.as_view(),
         name="service_checkin_edit"),
    path("print-tag/<int:pk>/", ServicePrintTagView.as_view(),
         name="service_print_tag"),
    path("billing/<int:pk>/", ServiceBillingView.as_view(), name="service_billing"),
    path(
        "billing/<int:pk>/finalize/",
        ServiceFinalizeView.as_view(),
        name="service_finalize",
    ),
]
