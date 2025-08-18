import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def load_user_settings(path: str = "user_settings.json") -> Dict:
    path = os.path.join(os.path.dirname(__file__), "..", "user_settings.json")
    path = os.path.abspath(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Не удалось прочитать файл: {e}")
        return {e}


def get_date_range(date_str: str, period: str = "M") -> Tuple:
    """Возвращает диапозон дат взависимости от периода"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    end = pd.Timestamp(date)

    if period == "W":
        start = date - timedelta(days=end.weekday())
        week_end = start + timedelta(days=6)
        end = pd.Timestamp(min(week_end, end))
    elif period == "M":
        start = end.replace(day=1)
    elif period == "Y":
        start = end.replace(month=1, day=1)
    elif period == "ALL":
        start = pd.Timestamp.min
    else:
        raise ValueError("Неверный период. Допустимо: W, M, Y, ALL")

    return pd.Timestamp(start), pd.Timestamp(end)


def filter_data(df: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    """Фильтрует DataFrame по диапазону дат"""

    local = df.copy()
    mask = (local["date"] >= start_date) & (local["date"] <= end_date)
    return local.loc[mask]


def calc_expenses(df: pd.DataFrame) -> Dict:
    """Считаем расходы по категориям"""

    expenses = df[df["amount"] < 0].copy()
    expenses["amount"] = expenses["amount"].abs()

    # Основные категории (Топ-7)
    EXCLUDE = {"Наличные", "Переводы"}
    expenses_base = expenses[~expenses["category"].isin(EXCLUDE)]
    main_categories = expenses_base.groupby("category")["amount"].sum().nlargest(7)

    other = expenses[~expenses["category"].isin(main_categories.index)]
    other_sum = other["amount"].sum()

    result = {
        "total_amount": round(expenses["amount"].sum()),
        "main": [{"category": k, "amount": round(v)} for k, v in main_categories.items()],
        "transfers_and_cash": [
            {"category": "Наличные", "amount": round(expenses[expenses["category"] == "Наличные"]["amount"].sum())},
            {"category": "Переводы", "amount": round(expenses[expenses["category"] == "Переводы"]["amount"].sum())},
        ],
    }

    if other_sum > 0:
        result["main"].append({"category": "Остальное", "amount": round(other_sum)})

    return result


def get_currency_rates() -> List[Dict]:
    """Получаем текущие курсы валют через API"""

    api_key = os.getenv("API_KEY_CURRENCY")
    if not api_key:
        logger.warning("API_KEY_CURRENCY не найден")
        return []

    url = "https://api.apilayer.com/exchangerates_data/latest"
    headers = {"apikey": api_key}
    params = {"base": "USD"}  # Базовая валюта USD

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("success", True):
            error = data.get("error", {}).get("info", "Unknown error")
            logger.error(f"API error: {error}")
            return []

        rates = data.get("rates", {})

        return [
            {"currency": "USD", "rate": 1.0},
            {"currency": "EUR", "rate": round(rates.get("EUR", 0), 2)},
            {"currency": "RUB", "rate": round(rates.get("RUB", 0), 2)},
        ]

    except Exception as e:
        logger.error(f"Ошибка получения курсов валют: {str(e)}")
        return []


def get_stock_prices() -> List[Dict]:
    """Получаем текущие цены акций"""

    settings = load_user_settings()
    tickers = settings.get("user_stocks", ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"])
    api_key = os.getenv("API_KEY_STOCKS")

    if not api_key:
        logger.warning("API_KEY_STOCKS не найден")
        return [{"stock": t, "price": 0.0} for t in tickers]

    results = []
    url = "https://www.alphavantage.co/query"

    for ticker in tickers:
        try:
            params = {"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": api_key}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            price = float(data.get("Global Quote", {}).get("05. price", 0.0))
            results.append({"stock": ticker, "price": round(price, 2)})
        except Exception as e:
            logger.error(f"Не удалось получить цену для: {ticker}, {e}")
            results.append({"stock": ticker, "price": 0.0})  # Значение по умолчанию при ошибке
    return results
