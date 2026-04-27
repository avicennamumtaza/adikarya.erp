from django.db import transaction
from decimal import Decimal

from apps.inventory.models import Stock

def process_purchase_item(product, branch, qty_in, price_in):
    with transaction.atomic():
        # 1. Ambil data stok saat ini (Lock row untuk mencegah race condition)
        stock_obj, created = Stock.objects.select_for_update().get_or_create(
            product=product, 
            branch=branch
        )
        
        # 2. Ambil data HPP lama & Stok Total (global atau per branch, biasanya global untuk HPP)
        current_total_stock = product.total_stock_all_branches()
        current_hpp = product.base_price
        
        # 3. Hitung Moving Average Baru
        # Jika stok lama <= 0, maka HPP baru = Harga beli sekarang
        if current_total_stock <= 0:
            new_hpp = price_in
        else:
            total_value_old = Decimal(current_total_stock) * current_hpp
            total_value_new = total_value_old + (Decimal(qty_in) * Decimal(price_in))
            total_qty_new = current_total_stock + qty_in
            new_hpp = total_value_new / Decimal(total_qty_new)
        
        # 4. Update Product & Stock
        product.base_price = new_hpp
        product.save()
        
        stock_obj.quantity += qty_in
        stock_obj.save()