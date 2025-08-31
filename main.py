import json
import logging
from pathlib import Path

import pandas as pd

from src.reports import report_to_file, spending_by_weekly
from src.services import analyze_cashback
from src.views import events_page

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

FILE_PATH = DATA_DIR / "operations.xlsx"


# Для блока 'События'
EVENTS_DATE = "2021-01-15"
EVENTS_PERIOD = "M"
EVENTS_OUT_FILE = REPORTS_DIR / "output_events.json"

# Для кэшбэка
CASHBACK_YEAR = 2019
CASHBACK_MONTH = 6
CASHBACK_OUT_FILE = REPORTS_DIR / "cashback.json"

# Для отчета
WEEKDAY_DATE = "2020-06-08"
WEEKDAY_OUT_FILE = REPORTS_DIR / "weekday_spending.json"


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
    df_events = df_events.rename(
        columns={"Дата операции": "date", "Категория": "category", "Сумма операции": "amount"}
    )

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
        logger.info("Считаю отчёт 'траты по дням недели'...")
        try:
            raw_func = spending_by_weekly.__wrapped__
        except AttributeError:
            raw_func = spending_by_weekly
        wrapped = report_to_file(filename=str(WEEKDAY_OUT_FILE))(raw_func)
        _df = wrapped(df_raw, date=WEEKDAY_DATE)
        logger.info(f"Готово. Сохранён файл: {WEEKDAY_OUT_FILE}")

        try:
            print(_df.head(7).to_string(index=False))
        except Exception:
            print(_df.head(7))
    except Exception as e:
        logger.error(f"Ошибка в отчёте по дням недели: {e}")


if __name__ == "__main__":
    main()
