import os
import json
from datetime import datetime
from pymongo import MongoClient, UpdateOne

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client["sandbox"]

# Идемпотентная загрузка
with open("stocktake.json", encoding = 'utf-8') as f:
    stocktake = json.load(f)

operations = []
for item in stocktake:
    operations.append(
        UpdateOne(
            {"_id": item["sku"]},
            {"$set": {
                "sku": item["sku"],
                "counted": item["counted"],
                "counted_by": item.get("counted_by", "")
            }},
            upsert = True
        )
    )

if operations:
    db.stocktake.bulk_write(operations)
    print(f"Загружено в stocktake: {len(operations)} позиций")

warehouse = list(db.warehouse.find({}))
stocktake_map = {s["sku"]: s["counted"] for s in stocktake}

matched = []
shortage = []
surplus = []

for w in warehouse:
    sku = w["sku"]
    accounted = w["qty_accounted"]
    counted = stocktake_map.get(sku, 0)

    if counted == accounted:
        matched.append(sku)
    elif counted < accounted:
        shortage.append({
            "sku": sku,
            "accounted": accounted,
            "counted": counted,
            "diff": accounted - counted
        })
    else: 
        surplus.append({
            "sku": sku,
            "accounted": accounted,
            "counted": counted,
            "diff": counted - accounted 
        })

today = datetime.now().strftime("%Y-%m-%d")
now = datetime.now()

updated_count = 0
for item in shortage + surplus:
    sku = item["sku"]
    counted = item["counted"]
    result = db.warehouse.update_one(
        {"sku": sku},
        {"$set": {
            "qty_accounted": counted,
            "last_stocktake": now
        }}
    )
    updated_count += result.modified_count

print(f"Обновлено позиций: {updated_count}")
print(f"  сошлось: {len(matched)}")
print(f"недостаток: {len(shortage)}")
print(f" излишек: {len(surplus)}")

print("\n=== НЕДОСТАЧА ===")
for s in shortage:
    print(f"  {s['sku']}: учёт {s['accounted']}, факт {s['counted']}, разница -{s['diff']}")

print("\n=== ИЗЛИШЕК ===")
for s in surplus:
    print(f"  {s['sku']}: учёт {s['accounted']}, факт {s['counted']}, разница +{s['diff']}")

print("\n=== СОШЛОСЬ ===")
print(f"  {len(matched)}: {', '.join(matched)}")

zero_counted = [s["sku"] for s in stocktake if s["counted"] == 0]
if zero_counted:
    db.warehouse.update_many(
        {"sku": {"$in": zero_counted}},
        {"$set": {"available": False}}
    )
    print(f"Помечено available: false - {len(zero_counted)} позиций")

non_zero = [s["sku"] for s in stocktake if s["counted"] > 0]
if non_zero:
    db.warehouse.update_many(
        {"sku": {"$in": non_zero}},
        {"$unset": {"available": ""}}
    )

total_shortage = sum(s["diff"] for s in shortage)

db.stocktake_log.update_one(
    {"date": today},
    {"$set": {
        "date": today,
        "positions": len(warehouse),
        "mismatches": len(shortage) + len(surplus),
        "total_shortage": total_shortage
    }},
    upsert=True
)

print(f"Записано в stocktake_log за {today}")
print("Готово.")





