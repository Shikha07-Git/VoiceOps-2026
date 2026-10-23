import sys
sys.path.insert(0, '.')
from src.config import DATA_DIR
import csv, os

orders_file = os.path.join(DATA_DIR, 'orders.csv')
customers_file = os.path.join(DATA_DIR, 'customers.csv')

order = None
with open(orders_file, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['order_id'] == '89782837':
            order = row
            break

if order:
    print("Order found:")
    print(f"  order_id: {order['order_id']}")
    print(f"  customer_id: {order['customer_id']}")
    print(f"  delivery_pincode: {order['delivery_pincode']}")
    print(f"  status: {order['status']}")
    print(f"  payment_method: {order['payment_method']}")

    # Get phone
    with open(customers_file, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['customer_id'] == order['customer_id']:
                print(f"  phone: {row['phone']}")
                print(f"  phone last 4: {row['phone'][-4:]}")
                break
else:
    print("Order not found. Let me find a valid order...")
    with open(orders_file, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    print(f"First 5 order IDs: {[r['order_id'] for r in rows[:5]]}")
