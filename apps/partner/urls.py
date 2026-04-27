from django.urls import path

from .views import (
    PartnerCreateView,
    PartnerDeleteView,
    PartnerExportView,
    PartnerListView,
    PartnerUpdateView,
)

app_name = "partner"

urlpatterns = [
    path("", PartnerListView.as_view(), name="partner_list"),
    path("add/", PartnerCreateView.as_view(), name="partner_add"),
    path("<int:pk>/edit/", PartnerUpdateView.as_view(), name="partner_edit"),
    path("<int:pk>/delete/", PartnerDeleteView.as_view(), name="partner_delete"),
    path("export/", PartnerExportView.as_view(), name="partner_export"),
]
