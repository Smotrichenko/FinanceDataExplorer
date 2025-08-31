import json

import pandas as pd

from src.reports import report_to_file, spending_by_weekly


def test_spending_by_weekly_avg(df_ops_ru):
    out = spending_by_weekly(df_ops_ru, date="2021-01-31")
    assert {"weekday", "average_spending"} <= set(out.columns)
    assert len(out) == 5
    assert (out["average_spending"] >= 0).all()


def test_report_to_file_writes(tmp_path):
    def toy_report():
        return pd.DataFrame([{"a": 1}, {"a": 2}])

    wrapped = report_to_file(filename=str(tmp_path / "toy.json"))(toy_report)
    res = wrapped()
    assert isinstance(res, pd.DataFrame)

    content = json.loads((tmp_path / "toy.json").read_text(encoding="utf-8"))
    assert isinstance(content, list) and content[0]["a"] == 1
