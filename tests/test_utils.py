import types

import pandas as pd
import pytest
import requests

from src import utils as utils_mod
from src.utils import calc_expenses, filter_data, get_currency_rates, get_date_range, get_stock_prices


@pytest.mark.parametrize(
    "date_str,period,expected_start,expected_end_prefix",
    [
        ("2021-08-15", "M", "2021-08-01", "2021-08"),
        ("2021-08-15", "Y", "2021-01-01", "2021-08"),
        ("2021-08-15", "W", "2021-08-09", "2021-08"),
    ],
)
def test_get_date_range_basic(date_str, period, expected_start, expected_end_prefix):
    start, end = get_date_range(date_str, period)
    assert str(start.date()) == expected_start
    assert str(end)[:7] == expected_end_prefix


def test_filter_data_inclusive_end(df_events):
    start = pd.Timestamp("2021-01-10")
    end = pd.Timestamp("2021-01-15")
    extra = pd.DataFrame([{"date": pd.Timestamp("2021-01-15"), "category": "Тест", "amount": -10.0}])
    df_local = pd.concat([df_events, extra], ignore_index=True)
    out = filter_data(df_local, start, end)
    assert not out.empty
    assert out["date"].max().date() == end.date()


def test_calc_expenses_excludes_cash_and_transfers(df_events):
    res = calc_expenses(df_events)
    cats = {item["category"] for item in res["main"]}
    assert "Наличные" not in cats
    assert "Переводы" not in cats
    total_neg = abs(df_events[df_events["amount"] < 0]["amount"]).sum()
    assert res["total_amount"] == round(total_neg)


def test_get_currency_rates_success(monkeypatch):
    monkeypatch.setenv("API_KEY_CURRENCY", "fake")

    def fake_get(url, headers=None, params=None, timeout=10):
        resp = types.SimpleNamespace()
        resp.raise_for_status = lambda: None
        resp.json = lambda: {"success": True, "rates": {"EUR": 0.9, "RUB": 90.0}}
        return resp

    monkeypatch.setattr(requests, "get", fake_get)
    rates = get_currency_rates()
    assert any(r["currency"] == "EUR" for r in rates)
    assert any(r["currency"] == "RUB" for r in rates)


def test_get_currency_rates_no_key(monkeypatch):
    monkeypatch.delenv("API_KEY_CURRENCY", raising=False)
    rates = get_currency_rates()
    assert rates == []


def test_get_stock_prices_success(monkeypatch):
    monkeypatch.setattr(utils_mod, "load_user_settings", lambda: {"user_stocks": ["AAPL", "MSFT"]})
    monkeypatch.setenv("API_KEY_STOCKS", "fake")

    def fake_get(url, params=None, timeout=10):
        sym = params["symbol"]
        price = 123.45 if sym == "AAPL" else 345.67
        resp = types.SimpleNamespace()
        resp.raise_for_status = lambda: None
        resp.json = lambda: {"Global Quote": {"05. price": str(price)}}
        return resp

    monkeypatch.setattr(requests, "get", fake_get)
    out = get_stock_prices()
    assert len(out) == 2
    assert out[0]["stock"] in {"AAPL", "MSFT"}
    assert out[0]["price"] > 0.0


def test_get_stock_prices_no_key(monkeypatch):
    monkeypatch.setattr(utils_mod, "load_user_settings", lambda: {"user_stocks": ["AAPL"]})
    monkeypatch.delenv("API_KEY_STOCKS", raising=False)
    out = get_stock_prices()
    assert out == [{"stock": "AAPL", "price": 0.0}]
