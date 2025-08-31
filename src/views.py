import logging
from pathlib import Path
from typing import Dict

import pandas as pd

from src.utils import calc_expenses, filter_data, get_currency_rates, get_date_range, get_stock_prices

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def events_page(input_date: str, period: str = "M", df: pd.DataFrame = None) -> Dict:
    """Главная функция для страницы 'События'"""
    if df is None:
        logger.error("Не передан DataFrame")
        raise ValueError("Не передан DataFrame")

    try:
        # Получаем диапазон дат
        start_date, end_date = get_date_range(input_date, period)
        logger.info(f"Обработка данных за период: {start_date} - {end_date}")

        # Фильтруем данные
        filtered_df = filter_data(df, start_date, end_date)
        logger.info(f"Найдено записей после фильтрации: {len(filtered_df)}")

        # Формируем ответ
        response = {
            "expenses": (
                calc_expenses(filtered_df)
                if not filtered_df.empty
                else {
                    "total_amount": 0,
                    "main": [],
                    "transfers_and_cash": [
                        {"category": "Наличные", "amount": 0},
                        {"category": "Переводы", "amount": 0},
                    ],
                }
            ),
            "income": {
                "total_amount": (
                    round(filtered_df[filtered_df["amount"] > 0]["amount"].sum()) if not filtered_df.empty else 0
                ),
                "main": (
                    [
                        {"category": k, "amount": round(v)}
                        for k, v in filtered_df[filtered_df["amount"] > 0]
                        .groupby("category")["amount"]
                        .sum()
                        .nlargest(10)
                        .items()
                    ]
                    if not filtered_df.empty
                    else []
                ),
            },
            "currency_rates": get_currency_rates(),
            "stock_prices": get_stock_prices(),
        }

        return response

    except Exception as e:
        logger.error(f"Ошибка при обработке данных: {str(e)}")
        return {"error": str(e)}
