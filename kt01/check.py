"""КТ-01 · приёмочная проверка.

Проверяет результат, а не способ: как именно вы получили состояние базы —
ваше дело. Правильные числа скрипт не печатает, только сообщает, сошлось или нет.
Ничего не меняет.

    bash ../stend/load.sh     # чистый учёт
    python3 inventory.py      # ваша работа
    python3 check.py          # эта проверка
"""

import json
import os
import pathlib
import sys

from pymongo import MongoClient

HERE = pathlib.Path(__file__).resolve().parent
URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")


def main():
    client = MongoClient(URI, serverSelectionTimeoutMS=4000)
    failed = 0

    def check(title, condition, hint=""):
        nonlocal failed
        if not condition:
            failed += 1
        print(f" {'✓' if condition else '✗'} {title}")
        if not condition and hint:
            print(f"     {hint}")

    try:
        sandbox = client["sandbox"]
        warehouse = sandbox["warehouse"]
        stocktake = sandbox["stocktake"]
        log = sandbox["stocktake_log"]

        counted = {
            item["sku"]: item["counted"]
            for item in json.loads((HERE / "stocktake.json").read_text(encoding="utf-8"))
        }
        zero_skus = {sku for sku, qty in counted.items() if qty == 0}

        print("Шаг 1 · пересчёт загружен")
        check("коллекция sandbox.stocktake заполнена",
              stocktake.count_documents({}) == len(counted),
              f"документов в коллекции: {stocktake.count_documents({})}, а в файле: {len(counted)}")
        check("повторная загрузка не задвоила данные",
              stocktake.count_documents({}) <= len(counted),
              "используйте свой _id или очищайте коллекцию перед загрузкой")

        print("\nШаг 3 · учёт приведён в соответствие")
        actual = {
            item["sku"]: item.get("qty_accounted")
            for item in warehouse.find({}, {"_id": 0, "sku": 1, "qty_accounted": 1})
        }
        mismatched = [sku for sku, qty in counted.items() if actual.get(sku) != qty]
        check("учётные остатки совпали с фактом по всем позициям",
              not mismatched,
              "учёт ещё не совпадает с пересчётом: сверьте qty_accounted с полем counted по каждому артикулу")
        check("отметка о дате инвентаризации проставлена",
              warehouse.count_documents({"last_stocktake": {"$exists": True}}) > 0,
              "поле last_stocktake должно появиться у позиций с расхождением")
        check("позиции без расхождений не переписаны без нужды",
              warehouse.count_documents({"last_stocktake": {"$exists": True}}) <= 6,
              "правка должна касаться только тех позиций, где учёт разошёлся с фактом")

        print("\nШаг 4 · пустые полки помечены")
        marked = {
            item["sku"]
            for item in warehouse.find({"available": False}, {"_id": 0, "sku": 1})
        }
        check("помечены все позиции с нулевым фактом", zero_skus <= marked,
              "не у всех позиций с нулевым пересчётом стоит available: false")
        check("лишние позиции не помечены", not (marked - zero_skus),
              "под пометку попали позиции, на которых товар есть")

        print("\nШаг 5 · журнал инвентаризации")
        check("в журнале ровно одна запись", log.count_documents({}) == 1,
              f"записей в sandbox.stocktake_log: {log.count_documents({})}; "
              "повторный запуск не должен добавлять вторую")
        entry = log.find_one({}) or {}
        check("в записи журнала есть дата и числа",
              all(key in entry for key in ("date", "positions", "mismatches")),
              "ожидаются поля date, positions, mismatches")

        print("\nЭталонные базы")
        check("shop.products не тронута", client["shop"]["products"].count_documents({}) == 21,
              "правки должны идти только в sandbox; восстановите базы (глава 1.0 справочника, §8)")
        check("shop.orders не тронута", client["shop"]["orders"].count_documents({}) == 120)

        print()
        if failed:
            print(f"Не сошлось: {failed}. Работа возвращается на доработку.")
        else:
            print("Всё сошлось. Осталось сдать отчёт inventory.md.")
    finally:
        client.close()

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
