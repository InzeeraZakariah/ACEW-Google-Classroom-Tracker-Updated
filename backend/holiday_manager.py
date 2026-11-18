import os
from typing import Any, Dict, List
from store_data import load_json, save_json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FILE = os.path.join(DATA_DIR, "holidays.json")


class HolidayManager:
    """
    Simple store of holiday dates the dean maintains — shown on the
    Holiday Calendar screen so upcoming due dates can be planned
    around them.
    """

    @staticmethod
    def load() -> List[Dict[str, Any]]:
        if not os.path.exists(FILE):
            return []
        try:
            with open(FILE, "r", encoding="utf-8") as file:
                data = load_json(file)
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        return [item for item in data if isinstance(item, dict) and item.get("date")]

    @staticmethod
    def save(data: List[Dict[str, Any]]) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(FILE, "w", encoding="utf-8") as file:
            save_json(data, file, indent=4, ensure_ascii=False)

    @staticmethod
    def add_holiday(date: str, name: str) -> Dict[str, Any]:
        """date: ISO "yyyy-mm-dd". Overwrites the name if that date is
        already a holiday, rather than creating a duplicate entry."""
        data = HolidayManager.load()
        record = {"date": date, "name": name}

        for item in data:
            if item.get("date") == date:
                item.update(record)
                HolidayManager.save(data)
                return item

        data.append(record)
        data.sort(key=lambda h: h.get("date", ""))
        HolidayManager.save(data)
        return record

    @staticmethod
    def delete_holiday(date: str) -> bool:
        data = HolidayManager.load()
        filtered = [item for item in data if item.get("date") != date]
        if len(filtered) == len(data):
            return False
        HolidayManager.save(filtered)
        return True

    @staticmethod
    def list_holidays() -> List[Dict[str, Any]]:
        return HolidayManager.load()

    @staticmethod
    def seed_indian_national_holidays(year: int) -> List[Dict[str, Any]]:
        """
        Adds India's fixed-date national/widely-observed holidays for
        the given year. Movable, lunar-calendar holidays (Diwali,
        Holi, Eid-ul-Fitr, Eid-ul-Adha, Good Friday, etc.) shift every
        year and can't be computed reliably without an external
        calendar source — those still need manual entry via
        add_holiday.
        """
        fixed_holidays = [
            (f"{year}-01-01", "New Year's Day"),
            (f"{year}-01-26", "Republic Day"),
            (f"{year}-05-01", "Labour Day"),
            (f"{year}-08-15", "Independence Day"),
            (f"{year}-10-02", "Gandhi Jayanti"),
            (f"{year}-12-25", "Christmas Day"),
        ]
        return [HolidayManager.add_holiday(date, name) for date, name in fixed_holidays]
