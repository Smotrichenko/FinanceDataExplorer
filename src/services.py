import json
import logging
from typing import Dict

import pandas as pd

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def analyze_cashback(data: pd.DataFrame, year: int, month: int) -> Dict[str, float]:
    """Анализ категорий с кэшбэком за указанный месяц"""

    logger.info(f"Запуск анализа кэшбэка за {month}.{year}")

    # Имена столбцов
    DATE = "Дата операции"
    CATEGORY = "Категория"
    AMOUNT = "Сумма операции"
    CASHBACK = "Бонусы (включая кэшбэк)"

    try:
        # Проверка обязательных столбцов
        required = [DATE, CATEGORY, AMOUNT, CASHBACK]
        missing = [i for i in required if i not in data.columns]
        if missing:
            error_message = f"Не найдены обязательные столцы: {missing}"
            logger.error(error_message)

        # Приведение типов
        df = data.copy()
        df[DATE] = pd.to_datetime(df[DATE], format="%d.%m.%Y %H:%M:%S", errors="coerce")
        df[AMOUNT] = pd.to_numeric(df[AMOUNT], errors="coerce")
        df[CASHBACK] = pd.to_numeric(df[CASHBACK], errors="coerce").fillna(0.0)
        df = df.dropna(subset=[DATE])

        # Выбор периода
        start = pd.Timestamp(year=year, month=month, day=1)
        end = (start + pd.offsets.MonthEnd(0)).replace(hour=23, minute=59, second=59, microsecond=999999)
        df = df.loc[(df[DATE] >= start) & (df[DATE] <= end)]
        logger.info(f"Фильтрация по периоду. Осталось строк: {len(df)}")

        # Оставляем только расходы
        df = df.loc[df[AMOUNT] < 0]
        logger.info(f"Фильтрация расходов. Осталось строк: {len(df)}")

        if len(df) == 0:
            logger.warning("Нет данных для анализа!")
            return {}

        # Суммарный начисленный кэшбэк по категориям
        grouped = (
            df.assign(cashback=df[CASHBACK].clip(lower=0))
            .groupby(CATEGORY, dropna=False)["cashback"]
            .sum()
            .sort_values(ascending=False)
        )

        # Формируем JSON-словарь с округлением и без пустых категорий
        result = {}
        for cat, val in grouped.items():
            if val > 0:
                key = str(cat) if pd.notna(cat) else "Без категории"
                result[key] = round(float(val), 2)

        logger.info(f"Анализ завершен. Найдено {len(result)} категорий с кэшбэком")

        return result

    except Exception as e:
        logger.critical(f"Критическая ошибка при анализе кэшбэка: {e}")
        raise


file_path = r"C:\Users\smotr\Desktop\FinanceDataExplorer\data\operations.xlsx"
df = pd.read_excel(file_path)
# analysis = analyze_cashback(df, 2020, 10)
#
# with open("cashback.json", "w", encoding="utf-8") as f:
#     json.dump(analysis, f, ensure_ascii=False, indent=4)
#     logger.info("Данные успешно сохранены в cashback.json")
