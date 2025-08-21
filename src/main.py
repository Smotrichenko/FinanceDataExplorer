import json
import os
import logging
import pandas as pd

from src.views import events_page
from src.services import analyze_cashback
from src.reports import spending_by_weekly


# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "..", "data", "operations.xlsx")
FILE_PATH = os.path.abspath(FILE_PATH)


# Для блока 'События'
EVENTS_DATE = "2021-08-30"
EVENTS_PERIOD = "M"
EVENTS_OUT_FILE = "output.json"

# Для кэшбэка
CASHBACK_YEAR = 2021
CASHBACK_MONTH = 11
CASHBACK_OUT_FILE = "cashback.json"

# Для отчета
WEEKDAY_DATE = "2021-04-30"


def main():
    logger.info(f"Загружаю данные из: {FILE_PATH}")
    try:
        df_raw = pd.read_excel(FILE_PATH)
    except Exception as e:
        logger.error(f"Не удалось загрузить файл Excel: {e}")
        return
    logger.info(f"Файл загружен. Всего строк: {len(df_raw)}")

    df_events = df_raw.copy()
    df_events.columns = df_events.columns.str.strip()
    df_events = df_events.rename(columns={
        "Дата операции": "date",
        "Категория": "category",
        "Сумма операции": "amount"
    })

    if "date" in df_events.columns:
        df_events["date"] = pd.to_datetime(df_events["date"], errors="coerce", dayfirst=True)
    if "amount" in df_events.columns:
        df_events["amount"] = pd.to_numeric(df_events["amount"], errors="coerce")

    df_events = df_events.dropna(subset=["date", "amount"])
    logger.info(f"Подготовлен файл для events_page. Всего строк: {len(df_events)}")

    try:
        logger.info("Считаю блок 'События'")
        events_result = events_page(EVENTS_DATE, EVENTS_PERIOD, df_events)
        with open(EVENTS_OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(events_result, f, ensure_ascii=False, indent=4)
        logger.info(f"Готово. Сохранен файл: {EVENTS_OUT_FILE}")
    except Exception as e:
        logger.error(f"Ошибка в events_page: {e}")


    try:
        logger.info("Считаю кэшбэк по категориям за месяц")
        cashback_result = analyze_cashback(df_raw, CASHBACK_YEAR, CASHBACK_MONTH)
        with open(CASHBACK_OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(cashback_result, f, ensure_ascii=False, indent=4)
        logger.info(f"Готово. Сохранен файл: {CASHBACK_OUT_FILE}")
    except Exception as e:
        logger.error(f"Ошибка в анализе кэшбэка: {e}")


    try:
        logger.info("Считаю отчет: 'траты по дням недели' (за последние 3 месяца)")
        report_df = spending_by_weekly(df_raw, date=WEEKDAY_DATE)

        try:
            print(report_df.head(7).to_string(index=False))
        except Exception:
            print(report_df.head(7))
        logger.info("Готово. Файл отчета сохранен: weekday_spending.json")
    except Exception as e:
        logger.error(f"Ошибка в отчете: {e}")


if __name__ == "__main__":
    main()



