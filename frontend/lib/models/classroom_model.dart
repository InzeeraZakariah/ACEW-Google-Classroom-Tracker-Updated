class MaterialItem {
  final String title;
  final String date;
  final int? unit;

  MaterialItem({
    required this.title,
    required this.date,
    this.unit,
  });

  factory MaterialItem.fromJson(Map<String, dynamic> json) {
    return MaterialItem(
      title: json["title"]?.toString() ?? "",
      date: json["date"]?.toString() ?? "",
      unit: json["unit"] is int
          ? json["unit"]
          : int.tryParse(
              json["unit"]?.toString() ?? "",
            ),
    );
  }
}


// QA ITEM
class QAItem {
  final String title;
  final String unit;
  final String part;
  final String qaType;
  final String date;

  QAItem({
    required this.title,
    required this.unit,
    required this.part,
    required this.qaType,
    required this.date,
  });

  factory QAItem.fromJson(Map<String, dynamic> json) {
    return QAItem(
      title: json["title"]?.toString() ?? "",
      unit: json["unit"]?.toString() ?? "",
      part: json["part"]?.toString() ?? "",
      // Backend sends the QA type marker under the key "type"
      // (e.g. "Q&A", "MCQ Q&A") — not "qa_type".
      qaType: json["type"]?.toString() ?? "",
      date: json["date"]?.toString() ?? "",
    );
  }
}


// DUPLICATE ITEM
class DuplicateItem {
  // Notes / Assignment duplicates come back from the backend as
  // {"title", "count"}. QA duplicates come back as
  // {"unit", "part", "type", "count"} — no "title" key at all.
  // This class parses either shape, and `label` gives you the right
  // display string regardless of which one it was.
  final String title;
  final String unit;
  final String part;
  final String qaType;
  final int count;

  DuplicateItem({
    required this.title,
    required this.unit,
    required this.part,
    required this.qaType,
    required this.count,
  });

  factory DuplicateItem.fromJson(
    Map<String, dynamic> json,
  ) {
    return DuplicateItem(
      title: json["title"]?.toString() ?? "",
      unit: json["unit"]?.toString() ?? "",
      part: json["part"]?.toString() ?? "",
      qaType: json["type"]?.toString() ?? "",
      count: json["count"] is int ? json["count"] : int.tryParse(json["count"]?.toString() ?? "",) ?? 0,
    );
  }

  /// Display label: the plain title for notes/assignments, or the
  /// "Unit-1 Part-A Q&A" style composite for QA duplicates (skipping
  /// any empty piece, e.g. when there's no Part).
  String get label {
    if (title.isNotEmpty) {
      return title;
    }

    return [unit, part, qaType]
        .where((piece) => piece.isNotEmpty)
        .join(" ");
  }
}

// PENDING SECTION
class PendingSection {
  final int uploaded;
  final int total;
  final List<dynamic> pending;

  PendingSection({
    required this.uploaded,
    required this.total,
    required this.pending,
  });

  factory PendingSection.fromJson(
    dynamic value,
  ) {
    // --------------------------------------------------------
    // Backend may return a List directly
    // Example: ["Unit-4 Notes", "Unit-5 Notes"]
    // --------------------------------------------------------
    if (value is List) {
      return PendingSection(
        uploaded: 0,
        total: 0,
        pending: List<dynamic>.from(value),
      );
    }

    // Backend may return a Map
    if (value is Map) {
      return PendingSection(
        uploaded: value["uploaded"] is int
            ? value["uploaded"]
            : int.tryParse(
                  value["uploaded"]?.toString() ?? "",
                ) ??
                0,

        total: value["total"] is int
            ? value["total"]
            : int.tryParse(
                  value["total"]?.toString() ?? "",
                ) ??
                0,

        pending: value["pending"] is List
            ? List<dynamic>.from(
                value["pending"],
              )
            : [],
      );
    }

    // Null / invalid
    return PendingSection(
      uploaded: 0,
      total: 0,
      pending: [],
    );
  }
}


// DUPLICATE GROUP
class DuplicateGroup {
  final List<DuplicateItem> notes;
  final List<DuplicateItem> assignments;
  final List<DuplicateItem> qa;

  DuplicateGroup({
    required this.notes,
    required this.assignments,
    required this.qa,
  });

  factory DuplicateGroup.fromJson(
    dynamic value,
  ) {
    if (value is! Map) {
      return DuplicateGroup(
        notes: [],
        assignments: [],
        qa: [],
      );
    }

    return DuplicateGroup(
      notes: _duplicateList(
        value["notes"],
      ),

      assignments: _duplicateList(
        value["assignments"],
      ),

      qa: _duplicateList(
        value["qa"],
      ),
    );
  }

  static List<DuplicateItem> _duplicateList(
    dynamic value,
  ) {
    if (value is! List) {
      return [];
    }

    return value
        .whereType<Map>()
        .map(
          (e) => DuplicateItem.fromJson(
            Map<String, dynamic>.from(e),
          ),
        )
        .toList();
  }
}

// PENDING DATA
class PendingData {
  final PendingSection notes;
  final PendingSection assignments;
  final PendingSection qa;
  final String status;

  PendingData({
    required this.notes,
    required this.assignments,
    required this.qa,
    required this.status,
  });

  factory PendingData.fromJson(
    dynamic value,
  ) {
    if (value is! Map) {
      return PendingData(
        notes: PendingSection.fromJson(null),
        assignments: PendingSection.fromJson(null),
        qa: PendingSection.fromJson(null),
        status: "Pending",
      );
    }

    return PendingData(
      notes: PendingSection.fromJson(
        value["notes"],
      ),

      assignments: PendingSection.fromJson(
        value["assignments"],
      ),

      qa: PendingSection.fromJson(
        value["qa"],
      ),

      status: value["status"]?.toString() ?? "Pending",
    );
  }
}

// CLASSROOM MODEL
class ClassroomModel {
  final String className;
  final String staffName;
  final String subject;

  final List<MaterialItem> notes;
  final List<MaterialItem> assignments;
  final List<QAItem> qa;

  final DuplicateGroup duplicates;
  final PendingData pending;

  ClassroomModel({
    required this.className,
    required this.staffName,
    required this.subject,
    required this.notes,
    required this.assignments,
    required this.qa,
    required this.duplicates,
    required this.pending,
  });

  factory ClassroomModel.fromJson(
    Map<String, dynamic> json,
  ) {
    return ClassroomModel(
      className: json["class_name"]?.toString() ?? json["course_name"]?.toString() ?? "",
      staffName: json["staff_name"]?.toString() ?? "",
      subject:   json["subject"]?.toString() ?? "",
      notes: _materialList(json["notes"],),
      assignments: _materialList(json["assignments"],),
      qa: _qaList(json["qa"],),
      duplicates: DuplicateGroup.fromJson(json["duplicates"],),
      pending: PendingData.fromJson(json["pending"],),
    );
  }

  // MATERIAL LIST
  static List<MaterialItem> _materialList(dynamic value,) {
    if (value is! List) {
      return [];
    }

    return value
        .whereType<Map>()
        .map(
          (e) => MaterialItem.fromJson(
            Map<String, dynamic>.from(e),
          ),
        ).toList();
  }

  // QA LIST
  static List<QAItem> _qaList(
    dynamic value,
  ) {
    if (value is! List) {
      return [];
    }

    return value
        .whereType<Map>()
        .map(
          (e) => QAItem.fromJson(
            Map<String, dynamic>.from(e),
          ),
        ).toList();
  }
}
