import json
import os
import re
import threading

FILTERS_FILE = "filters.json"

KINDS = ("departments", "years", "sections")

ROMAN_ORDER = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
_SECTION = re.compile(r"^[A-Z0-9]{1,3}$")

# The lists the app shipped with. Used only until the first change is
# saved; after that filters.json is the source of truth.
DEFAULTS = {
    "departments": ["AI&DS", "CSE", "ECE", "EEE", "IT", "CIVIL", "MBA", "MCA",
                    "ME-PED", "ME-CS", "ME-CEM", "ME-VLSI", "ME-CMS", "ME-AE"],
    "years": ["I", "II", "III", "IV"],
    "sections": ["A", "B", "C", "D"],
}

_lock = threading.Lock()


class DuplicateError(ValueError):
    """The value is already in the list."""


def _load() -> dict:
    if os.path.exists(FILTERS_FILE):
        try:
            with open(FILTERS_FILE, "r") as f:
                data = json.load(f)
            return {k: list(data.get(k) or DEFAULTS[k]) for k in KINDS}
        except Exception:
            pass
    return {k: list(v) for k, v in DEFAULTS.items()}


def _save(data: dict):
    with open(FILTERS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def _normalize(kind: str, value) -> str:
    v = str(value or "").strip().upper()

    if kind == "departments":
        if not v:
            raise ValueError("Department name is required")
        # Year:Department pairs are sent as "III:CSE,II:IT", so a
        # name containing ',' or ':' would break that parsing.
        if re.search(r"[\s,:]", v):
            raise ValueError("Department name can't contain spaces, commas or colons")
    elif kind == "years":
        if v not in ROMAN_ORDER:
            raise ValueError("Year must be a roman numeral from I to X")
    else:
        if not _SECTION.match(v):
            raise ValueError("Section must be 1-3 letters or digits, e.g. E or C1")

    return v


def _ordered(kind: str, items: list) -> list:
    if kind == "years":
        return sorted(items, key=lambda y: ROMAN_ORDER.index(y) if y in ROMAN_ORDER else 99)
    if kind == "sections":
        return sorted(items)
    return items  # departments keep the order they were defined in


class FilterManager:

    @staticmethod
    def get_all() -> dict:
        data = _load()
        return {k: _ordered(k, data[k]) for k in KINDS}

    @staticmethod
    def add(kind: str, value) -> str:
        value = _normalize(kind, value)
        with _lock:
            data = _load()
            if value.lower() in (v.lower() for v in data[kind]):
                raise DuplicateError(f"'{value}' already exists")
            data[kind].append(value)
            data[kind] = _ordered(kind, data[kind])
            _save(data)
        return value

    @staticmethod
    def remove(kind: str, value) -> bool:
        """Removes one value. Returns False if it wasn't in the list.
        Does not cascade - schedules that mention it are left as-is."""
        target = str(value or "").strip().lower()
        with _lock:
            data = _load()
            kept = [v for v in data[kind] if v.lower() != target]
            if len(kept) == len(data[kind]):
                return False
            if not kept:
                raise ValueError(f"Can't remove the last {kind[:-1]} - at least one is needed")
            data[kind] = kept
            _save(data)
        return True