from src import views as views_mod


def test_events_page_happy_path(monkeypatch, df_events, tmp_path):
    # подменяем курсы и котировки
    monkeypatch.setattr(views_mod, "get_currency_rates", lambda: [{"currency": "USD", "rate": 1.0}])
    monkeypatch.setattr(views_mod, "get_stock_prices", lambda: [{"stock": "AAPL", "price": 123.45}])

    res = views_mod.events_page("2021-01-30", "M", df_events)
    # минимальные проверки структуры
    assert "expenses" in res and "income" in res
    assert "currency_rates" in res and "stock_prices" in res
    assert isinstance(res["expenses"]["total_amount"], (int, float))
