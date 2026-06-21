from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('dashboard/', views.FinanceDashboardView.as_view(), name='dashboard'),
    path('transaction/new/', views.GeneralTransactionCreateView.as_view(), name='transaction_create'),
    path('transaction/<int:pk>/', views.FinanceTransactionDetailView.as_view(), name='transaction_detail'),
    path('print-experiment/', views.PrintExperimentView.as_view(), name='print_experiment'),
]