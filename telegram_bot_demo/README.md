# Telegram decision-tree bot — prototype

Малко демо: Telegram бот, който превежда потребителя през тривиално,
ежедневно решение ("какво да ям днес?") чрез дърво от 3 нива с inline
бутони, плюс логване на всяка стъпка за drop-off анализ.

Отделен, самостоятелен прототип — не е част от WKB договора (`wkb.py`
в корена на repo-то); двете не споделят схема.

## Файлове

- `tree.json` — самото дърво (node id -> текст + опции)
- `engine.py` — четене на дървото и навигация, без зависимост от Telegram
- `steplog.py` — append-only JSONL лог на всяка стъпка (`steps.jsonl`)
- `bot.py` — истинският Telegram бот (изисква `BOT_TOKEN`)
- `simulate.py` — CLI симулатор на същото дърво, без нужда от токен
- `analyze.py` — drop-off funnel от `steps.jsonl`

## Пусни локално без Telegram

```
pip install -r requirements.txt   # само за bot.py; simulate.py няма нужди
python simulate.py --user-id 1
python simulate.py --user-id 2
python analyze.py
```

## Пусни истинския бот

1. Вземи token от [@BotFather](https://t.me/BotFather)
2. `BOT_TOKEN=<token> python bot.py`
3. Пиши `/start` на бота в Telegram

Всяка стъпка (старт, избор, невалиден вход, рестарт, достигане до
резултат) се логва в `steps.jsonl`. `python analyze.py` показва колко
сесии са достигнали всеки възел и колко са "паднали" там, без да
продължат.
