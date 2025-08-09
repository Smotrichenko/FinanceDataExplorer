import json
import logging
from datetime import datetime, timedelta
from idlelib.rpc import response_queue
from typing import Dict, List, Tuple

import pandas as pd
import requests

# Настройка логирования
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelnames)s - %(message)s')

def get_date_range(date_str: str, period: str = 'M') -> Tuple:
    """Возвращает диапозон дат взависимости от периода"""
    date = datetime.strptime(date_str, '%Y-%m-%d')

    if period == 'W':
        start = date - timedelta(days=date.weekday())
        end = start + timedelta(days=6)
    elif period == 'M':
        start = date.replace(day=1)
        end = date
    elif period == 'Y':
        start = date.replace(month=1, day=1)
        end = date
    elif period == 'ALL':
        start = datetime.min
        end = date
    else:
        raise ValueError("Неверный период. Допустимо: W, M, Y, ALL")

    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')


def filter_data(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    """Фильтрует DataFrame по диапазону дат"""
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    return df.loc[mask]


def calc_expenses(df: pd.DataFrame) -> Dict:
    """Считаем расходы по категориям"""
    expenses = df[df['amount'] < 0]. copy()
    expenses['amount'] = expenses['amount'].abs()

    #Основные категории (Топ-7)
    main_categories = expenses.grouby('category')['amount'].sum().nlargest(7)
    other = expenses[~expenses['category'].isin(main_categories.index)]
    other_sum = other['amount'].sum()

    result = {
        "total_amount": round((expenses['amount'].sum())),
        "main": [{"category": k, "amount": round(v)} for k, v in main_categories.items()]

        "transfers_and_cash": [
            {"category": "Наличные", "amount": round(expenses[expenses['categories'] ==
            'Наличные']['amount'].sum())},
            {"category": "Переводы", "amount": round(expenses[expenses['category'] ==
            'Переводы']['amount'].sum())}
        ]
    }

    if other_sum > 0:
        result["main"].append({"category": "Остальное", "amount": round(other_sum)})

    return result


def get_currency_rates(api_key: str) -> List:
    """Получаем текущие курсы валют через API"""
    URL = "https://api.apilayer.com/exchangerates_data/latest"
    headers = {"apikey": API_KEY}

    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
        data = response.json()

        if not data.get('success', False):
            logging.error(f"API ошибка: {data.get('error', {}).get('info', 'Unknown error')}")
            return []

        base_currency = data['base']
        rates = data['rates']

        result = []
        for currency in ['USD', 'EUR']:
            if currency == base_currency:
                rate = 1.0
            else:
                rate = rates.get(currency)
                if not rate:
                    continue

            result.append({
                "currency": currency,
                "rate": round(rate, 2)
            })

        return result

    except (KeyError, ValueError) as e:
        logging.error(f"Ошибка обработки данных: {e}")

    return []


def get_stock_prices(api_key) -> List:
    """Получаем текущие цены акций"""
    stocks = ['AAPL', 'AMZN', 'GOOGL', 'MSFT', 'TSLA']

    try:
        return [
            {"stock": stock, "price": round(float(requests.get(f'https://api.stockdata.org/v1/data/quote?symbols={stock}').json()['data'][0]['price']), 2)}
            for stock in stocks
        ]
    except Exception as e:
        logging.error(f"Ошибка получения акций: {e}")
        return []
