from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .models import Contact
from .services import (
    PartnerForm,
    apply_filters,
    build_export_response,
    initialize_form,
    paginate_contacts,
    partner_stats,
    save_form,
)


class PartnerListView(View):
    template_name = "partner/partner_list.html"

    def get(self, request):
        queryset = Contact.objects.all().order_by("name")
        filtered_queryset = apply_filters(queryset, request.GET)
        partners_page = paginate_contacts(
            filtered_queryset, request.GET.get("page"), per_page=10)

        context = {
            "partners": partners_page,
            **partner_stats(),
        }
        return render(request, self.template_name, context)


class PartnerCreateView(View):
    template_name = "partner/partner_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": initialize_form(), "partner": None})

    def post(self, request):
        form = PartnerForm(request.POST)
        if form.is_valid():
            save_form(form)
            messages.success(request, "Partner berhasil ditambahkan.")
            return redirect("partner_list")
        return render(request, self.template_name, {"form": form, "partner": None})


class PartnerUpdateView(View):
    template_name = "partner/partner_form.html"

    def get(self, request, pk):
        partner = get_object_or_404(Contact, pk=pk)
        form = initialize_form(partner)
        return render(request, self.template_name, {"form": form, "partner": partner})

    def post(self, request, pk):
        partner = get_object_or_404(Contact, pk=pk)
        form = PartnerForm(request.POST)
        if form.is_valid():
            save_form(form, contact=partner)
            messages.success(request, "Partner berhasil diperbarui.")
            return redirect("partner_list")
        return render(request, self.template_name, {"form": form, "partner": partner})


class PartnerDeleteView(View):
    def post(self, request, pk):
        partner = get_object_or_404(Contact, pk=pk)
        partner.delete()
        messages.success(request, "Partner berhasil dihapus.")
        return redirect("partner_list")

    def delete(self, request, pk):
        return self.post(request, pk)


class PartnerExportView(View):
    def get(self, request):
        queryset = Contact.objects.all().order_by("name")
        filtered_queryset = apply_filters(queryset, request.GET)
        return build_export_response(filtered_queryset)
