import os
from typing import Any, Dict, List
from store_data import load_json, save_json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FILE = os.path.join(DATA_DIR, "commencement_dates.json")


class CommencementManager:
    """
    Academic commencement dates the dean marks on the calendar — e.g.
    the start of an academic year or semester. Kept as a list rather
    than a single value since the dean may mark more than one over
    time (a new commencement each academic year), each with its own
    label.
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
    def add(date: str, label: str) -> Dict[str, Any]:
        """date: ISO "yyyy-mm-dd". Overwrites the label if that date is
        already marked, rather than creating a duplicate entry."""
        data = CommencementManager.load()
        record = {"date": date, "label": label}

        for item in data:
            if item.get("date") == date:
                item.update(record)
                CommencementManager.save(data)
                return item

        data.append(record)
        data.sort(key=lambda e: e.get("date", ""))
        CommencementManager.save(data)
        return record

    @staticmethod
    def delete(date: str) -> bool:
        data = CommencementManager.load()
        filtered = [item for item in data if item.get("date") != date]
        if len(filtered) == len(data):
            return False
        CommencementManager.save(filtered)
        return True

    @staticmethod
    def list_all() -> List[Dict[str, Any]]:
        return CommencementManager.load()
