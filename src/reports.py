import json
import logging
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

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


def report_to_file(func=None, *, filename: Optional[str] = None):
    """Декоратор для сохранения отчетов в файл"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"Запуск отчётной функции: {func.__name__}")
            result = func(*args, **kwargs)
            out_name = filename
            if not out_name:
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_name = f"report_{func.__name__}_{current_time}.json"

            if isinstance(result, pd.DataFrame):
                result.to_json(out_name, orient="records", force_ascii=False, indent=2)
            else:
                with open(out_name, "w", encoding="utf-8") as fp:
                    json.dump(result, fp, ensure_ascii=False, indent=2)

            print(f"Отчет сохранен в файл: {out_name}")
            return result

        return wrapper

    return decorator


@report_to_file(filename="weekday_spending.json")
def spending_by_weekly(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """Функция анализирует средние траты по дням недели за последние 3 месяца"""
    logger.info("Начало формирования отчёта: траты по дням недели")

    # Имена столбцов, которые ожидаем
    DATE_COL = "Дата операции"
    AMOUNT_COL = "Сумма операции"

    # Приведение типов и проверка
    df = transactions.copy()
    if DATE_COL not in df.columns or AMOUNT_COL not in df.columns:
        logger.error("Отсутствуют обязательные колонки в DataFrame")
        raise KeyError(f"В датафрейме должны быть столбцы: '{DATE_COL}', '{AMOUNT_COL}'")

    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce", dayfirst=True)
    df[AMOUNT_COL] = pd.to_numeric(df[AMOUNT_COL], errors="coerce")
    df = df.dropna(subset=[DATE_COL, AMOUNT_COL])

    # Определяем дату анализа
    end_date = pd.to_datetime(date) if date else pd.Timestamp.now()

    # Нормализуем границы
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    start_date = (end_date - pd.DateOffset(months=3)).replace(hour=0, minute=0, second=0, microsecond=0)
    logger.info(f"Анализируем период: {start_date.date()} — {end_date.date()}")

    # Фильтруем данные за последние 3 месяца
    df = df[(df[DATE_COL] >= start_date) & (df[DATE_COL] <= end_date)]
    if df.empty:
        logger.warning("Нет данных для выбранного периода")
        return pd.DataFrame(
            {
                "weekday": ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"],
                "average_spending": [0.0] * 7,
            }
        )

    # Оставляем только расходы, переводим в положительные величины (в рублях)
    df = df[df[AMOUNT_COL] < 0].copy()
    df["spend"] = (-df[AMOUNT_COL]).clip(lower=0)

    # Сумма трат за календарный день
    df["day"] = df[DATE_COL].dt.floor("D")
    daily = df.groupby("day", as_index=False)["spend"].sum()

    # День недели: 0=Пн..6=Вс
    daily["weekday_num"] = daily["day"].dt.weekday
    RU_WEEKDAYS = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }
    daily["weekday"] = daily["weekday_num"].map(RU_WEEKDAYS)

    # Средний дневной расход по каждому дню недели
    out = (
        daily.groupby(["weekday", "weekday_num"], as_index=False)["spend"]
        .mean()
        .rename(columns={"spend": "average_spending"})
        .sort_values("weekday_num")
        .loc[:, ["weekday", "average_spending"]]
        .reset_index(drop=True)
    )
    out["average_spending"] = out["average_spending"].round(2)
    logger.info("Отчёт сформирован.")
    return out
