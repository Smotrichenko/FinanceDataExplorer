import pandas as pd
import pytest
from datetime import datetime, timedelta


@pytest.fixture
def df_ops_ru() -> pd.DataFrame:
    """
    Русские колонки (как в исходном Excel) для services/reports:
    - Дата операции, Категория, Сумма операции, Бонусы (включая кэшбэк)
    """
    base = datetime(2021, 1, 10, 12, 0, 0)
    rows = [
        # расход с кешбэком
        {"Дата операции": base,              "Категория":"Супермаркеты", "Сумма операции": -1000.00, "Бонусы (включая кэшбэк)": 50, "Кэшбэк": None},
        # доход (не должен участвовать в расходах/кешбэке)
        {"Дата операции": base + timedelta(days=1), "Категория":"Зарплата",     "Сумма операции":  50000.00, "Бонусы (включая кэшбэк)": 0,  "Кэшбэк": None},
        # расход без preferred кешбэка, но с fallback "Кэшбэк"
        {"Дата операции": base + timedelta(days=2), "Категория":"Аптеки",       "Сумма операции":  -2000.00, "Бонусы (включая кэшбэк)": None, "Кэшбэк": 100},
        # Наличные (исключаем из top при расчёте расходов в utils.calc_expenses)
        {"Дата операции": base + timedelta(days=3), "Категория":"Наличные",     "Сумма операции":  -500.00,  "Бонусы (включая кэшбэк)": 0,  "Кэшбэк": 0},
        # Переводы (исключаем)
        {"Дата операции": base + timedelta(days=4), "Категория":"Переводы",     "Сумма операции":  -800.00,  "Бонусы (включая кэшбэк)": 0,  "Кэшбэк": 0},
        # ещё один расход в супермаркетах
        {"Дата операции": base + timedelta(days=5), "Категория":"Супермаркеты", "Сумма операции":  -700.00,  "Бонусы (включая кэшбэк)": 35, "Кэшбэк": None},
    ]
    df = pd.DataFrame(rows)
    return df


@pytest.fixture
def df_events(df_ops_ru) -> pd.DataFrame:
    """
    Подготовленный df под events_page:
    - date, category, amount
    """
    df = df_ops_ru.rename(columns={
        "Дата операции": "date",
        "Категория": "category",
        "Сумма операции": "amount",
    }).copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    return df
