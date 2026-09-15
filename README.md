# Lesson 01 — MongoDB Compass

## Подключение
1. Открыть MongoDB Compass → New Connection.
2. Вставить строку подключения:
   mongodb://localhost:27017
3. Connect → выбрать базу `shopdb` (или создать её).

## Загрузка данных
1. В Compass выбрать базу `shopdb` → Create collection → имя `orders`.
2. Открыть коллекцию → кнопка **ADD DATA** → **Import JSON**.
3. Выбрать файл `seed.json` из этой папки → Import.
4. Убедиться, что счётчик документов = 5.

## Проверка запросов
В поле Filter вводить фильтры из `queries.md` по одному и сверять счётчик.

## Удаление коллекции
Правый клик по `orders` → Drop Collection → подтвердить.
