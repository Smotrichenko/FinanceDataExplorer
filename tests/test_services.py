import json

from src.services import analyze_cashback


def test_analyze_cashback_basic(df_ops_ru, tmp_path):
    res = analyze_cashback(df_ops_ru, 2021, 1)
    assert res.get("Супермаркеты") == 85.0

    # сериализация
    out = tmp_path / "cashback.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    assert out.exists()
