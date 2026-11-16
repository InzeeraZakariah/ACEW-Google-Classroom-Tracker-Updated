from collections import Counter


class DuplicateChecker:

    @staticmethod
    def _make_key(item):
        # Notes / Assignments
        if "title" in item:
            return ("title", item["title"].strip())

        # Question & Answer — Unit -> Part -> Type (e.g. Unit-3 / Part-B / Q&A)
        if "unit" in item:
            return (
                "qa",
                item.get("unit", "").strip(),
                item.get("part", "").strip(),
                item.get("type", "").strip(),
            )

        return None

    @staticmethod
    def find_duplicates(materials):

        counter = Counter()

        for item in materials:
            key = DuplicateChecker._make_key(item)
            if key is None:
                continue
            counter[key] += 1

        duplicates = []

        for key, count in counter.items():

            if count <= 1:
                continue

            if key[0] == "title":
                duplicates.append({
                    "title": key[1],
                    "count": count
                })

            else:
                _, unit, part, qtype = key
                duplicates.append({
                    "unit": unit,
                    "part": part,
                    "type": qtype,
                    "count": count
                })

        duplicates.sort(
            key=lambda x: x.get(
                "title",
                f"{x.get('unit', '')} {x.get('part', '')} {x.get('type', '')}"
            )
        )

        return duplicates

    @staticmethod
    def total_duplicates(materials):
        return len(DuplicateChecker.find_duplicates(materials))

    @staticmethod
    def has_duplicates(materials):
        return DuplicateChecker.total_duplicates(materials) > 0

    @staticmethod
    def duplicate_message(materials):

        duplicates = DuplicateChecker.find_duplicates(materials)

        if not duplicates:
            return "-"

        result = []

        for item in duplicates:

            if "title" in item:
                result.append(
                    f"{item['title']} ({item['count']} times)"
                )

            else:
                text = " ".join(
                    piece for piece in [
                        item.get("unit", ""),
                        item.get("part", ""),
                        item.get("type", "")
                    ] if piece
                )

                text += f" ({item['count']} times)"

                result.append(text)

        return "\n".join(result)