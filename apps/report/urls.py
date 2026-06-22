from django.urls import path
from . import views

app_name = 'report'
urlpatterns = [
    path('dashboard/', views.ReportDashboardView.as_view(), name='dashboard'),
    path('detail/', views.ReportDetailView.as_view(), name='detail'),
    path('analytics/', views.AnalyticsDashboardView.as_view(), name='analytics'),

    # ── Import / Export Hub ──
    path('data-hub/', views.DataHubView.as_view(), name='data_hub'),

    # ── Export endpoints ──
    path('export/products/', views.ExportProductsView.as_view(), name='export_products'),
    path('export/partners/', views.ExportPartnersView.as_view(), name='export_partners'),
    path('export/sales/', views.ExportSalesView.as_view(), name='export_sales'),
    path('export/purchases/', views.ExportPurchasesView.as_view(), name='export_purchases'),
    path('export/finance/', views.ExportFinanceView.as_view(), name='export_finance'),
    path('export/service/', views.ExportServiceView.as_view(), name='export_service'),

    # ── Import endpoints ──
    path('import/products/', views.ImportProductsView.as_view(), name='import_products'),
    path('import/partners/', views.ImportPartnersView.as_view(), name='import_partners'),
    path('import/sales/', views.ImportSalesView.as_view(), name='import_sales'),
    path('import/purchases/', views.ImportPurchasesView.as_view(), name='import_purchases'),
    path('import/finance/', views.ImportFinanceView.as_view(), name='import_finance'),
    path('import/service/', views.ImportServiceView.as_view(), name='import_service'),
]