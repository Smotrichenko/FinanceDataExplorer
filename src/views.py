import json
import logging
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


# Загрузка данных
try:
    df = pd.read_excel(
        r"C:\Users\smotr\Desktop\FinanceDataExplorer\data\operations.xlsx",
        parse_dates=True,
        dtype={"Сумма операции": float},
    )

    # Очистка и переименование
    df.columns = df.columns.str.strip()
    df.rename(columns={"Дата операции": "date", "Категория": "category", "Сумма операции": "amount"}, inplace=True)

    # Преобразование дат
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date", "amount"])


except Exception as e:
    logger.error(f"Ошибка загрузки данных: {str(e)}", exc_info=True)
    exit()

# Обработка и сохранение
# result = events_page("2021-05-30", "M", df)
#
# with open("output.json", "w", encoding="utf-8") as f:
#     json.dump(result, f, ensure_ascii=False, indent=4)
#     logger.info("Данные успешно сохранены в output.json")
