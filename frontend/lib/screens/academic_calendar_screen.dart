import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/report_downloader.dart';

String _iso(DateTime d) =>
    "${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}";

// "unit-1, Unit 2, 3" -> [1, 2, 3] — pulls the first number out of
// each comma-separated piece, so it accepts "unit-1", "Unit 1", "1",
// or "Assignment 1" alike. Pieces with no number are skipped.
List<int> _parseNumberList(String text) {
  final numberPattern = RegExp(r'(\d+)');
  return text
      .split(",")
      .map((piece) => piece.trim())
      .where((piece) => piece.isNotEmpty)
      .map((piece) => numberPattern.firstMatch(piece))
      .whereType<RegExpMatch>()
      .map((match) => int.parse(match.group(1)!))
      .toList();
}

// Year+Department pairs of a schedule entry. Older entries stored a
// `subjects` list instead of `pairs`, so fall back to deriving them.
List<Map<String, String>> _pairsOf(Map<String, dynamic> entry) {
  final result = <Map<String, String>>[];
  final seen = <String>{};

  void add(dynamic item) {
    final year = item["year"]?.toString() ?? "";
    final department = item["department"]?.toString() ?? "";
    if (year.isEmpty || department.isEmpty) return;
    if (seen.add("$year|$department")) {
      result.add({"year": year, "department": department});
    }
  }

  for (final p in (entry["pairs"] as List?) ?? const []) {
    add(p);
  }
  if (result.isEmpty) {
    for (final s in (entry["subjects"] as List?) ?? const []) {
      add(s);
    }
  }
  return result;
}

String _pairsLabel(Map<String, dynamic> entry) {
  final pairs = _pairsOf(entry);
  if (pairs.isEmpty) return "-";
  return pairs.map((p) => "${p['year']} + ${p['department']}").join(", ");
}

class AcademicCalendarScreen extends StatefulWidget {
  const AcademicCalendarScreen({super.key});

  @override
  State<AcademicCalendarScreen> createState() => _AcademicCalendarScreenState();
}

class _AcademicCalendarScreenState extends State<AcademicCalendarScreen> {
  DateTime visibleMonth = DateTime(DateTime.now().year, DateTime.now().month, 1);

  List<Map<String, dynamic>> holidays = [];
  List<Map<String, dynamic>> schedule = [];
  List<Map<String, dynamic>> commencementDates = [];

  bool isLoading = false;

  @override
  void initState() {
    super.initState();
    loadAll();
  }

  Future<void> loadAll() async {
    setState(() => isLoading = true);
    try {
      final results = await Future.wait([
        ApiService.getHolidays(),
        ApiService.getAcademicSchedule(),
        ApiService.getCommencementDates(),
      ]);
      if (!mounted) return;
      setState(() {
        holidays = results[0];
        schedule = results[1];
        commencementDates = results[2];
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to load calendar: $e"), backgroundColor: Colors.red),
      );
    }
    if (!mounted) return;
    setState(() => isLoading = false);
  }

  Map<String, dynamic>? _holidayOn(String iso) {
    for (final h in holidays) {
      if (h["date"] == iso) return h;
    }
    return null;
  }

  Map<String, dynamic>? _scheduleOn(String iso) {
    for (final s in schedule) {
      if (s["date"] == iso) return s;
    }
    return null;
  }

  Map<String, dynamic>? _commencementOn(String iso) {
    for (final c in commencementDates) {
      if (c["date"] == iso) return c;
    }
    return null;
  }

  void changeMonth(int delta) {
    setState(() {
      visibleMonth = DateTime(visibleMonth.year, visibleMonth.month + delta, 1);
    });
  }

  Future<void> addIndianHolidays() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text("Add Indian Holidays for ${visibleMonth.year}?"),
        content: const Text(
          "Adds the fixed-date national/widely-observed holidays "
          "(New Year, Republic Day, Labour Day, Independence Day, "
          "Gandhi Jayanti, Christmas). Movable holidays like Diwali, "
          "Holi, and Eid shift every year and need manual entry.",
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text("Cancel")),
          ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text("Add")),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await ApiService.seedIndianHolidays(visibleMonth.year);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Indian holidays added")),
      );
      await loadAll();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to add holidays: $e"), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> onDayTap(DateTime date) async {
    final iso = _iso(date);
    final holiday = _holidayOn(iso);
    final scheduleEntry = _scheduleOn(iso);
    final commencement = _commencementOn(iso);

    final action = await showDialog<String>(
      context: context,
      builder: (_) => SimpleDialog(
        title: Text(iso),
        children: [
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, "schedule"),
            child: Text(scheduleEntry == null ? "Set Academic Schedule (due date)" : "Edit Academic Schedule"),
          ),
          if (scheduleEntry != null)
            SimpleDialogOption(
              onPressed: () => Navigator.pop(context, "delete_schedule"),
              child: const Text("Remove Schedule", style: TextStyle(color: Colors.red)),
            ),
          const Divider(),
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, holiday == null ? "add_holiday" : "remove_holiday"),
            child: Text(holiday == null ? "Mark as Holiday" : "Remove Holiday (${holiday["name"]})"),
          ),
          const Divider(),
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, commencement == null ? "add_commencement" : "remove_commencement"),
            child: Text(
              commencement == null
                  ? "Mark as Academic Commencement"
                  : "Remove Commencement (${commencement["label"]})",
            ),
          ),
        ],
      ),
    );

    if (action == null) return;

    switch (action) {
      case "schedule":
        final saved = await Navigator.push<bool>(
          context,
          MaterialPageRoute(
            builder: (_) => _ScheduleEditorScreen(date: iso, existing: scheduleEntry),
          ),
        );
        if (saved == true) await loadAll();
        break;

      case "delete_schedule":
        try {
          await ApiService.deleteAcademicSchedule(iso);
          await loadAll();
        } catch (e) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text("Failed to remove schedule: $e"), backgroundColor: Colors.red),
          );
        }
        break;

      case "add_holiday":
        final nameController = TextEditingController();
        final name = await showDialog<String>(
          context: context,
          builder: (_) => AlertDialog(
            title: Text("Mark $iso as Holiday"),
            content: TextField(
              controller: nameController,
              autofocus: true,
              decoration: const InputDecoration(labelText: "Holiday Name", border: OutlineInputBorder()),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
              ElevatedButton(
                onPressed: () => Navigator.pop(context, nameController.text.trim()),
                child: const Text("Save"),
              ),
            ],
          ),
        );
        if (name == null || name.isEmpty) return;
        try {
          await ApiService.addHoliday(date: iso, name: name);
          await loadAll();
        } catch (e) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text("Failed to add holiday: $e"), backgroundColor: Colors.red),
          );
        }
        break;

      case "remove_holiday":
        try {
          await ApiService.deleteHoliday(iso);
          await loadAll();
        } catch (e) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text("Failed to remove holiday: $e"), backgroundColor: Colors.red),
          );
        }
        break;

      case "add_commencement":
        final labelController = TextEditingController();
        final label = await showDialog<String>(
          context: context,
          builder: (_) => AlertDialog(
            title: Text("Mark $iso as Commencement"),
            content: TextField(
              controller: labelController,
              autofocus: true,
              decoration: const InputDecoration(
                labelText: "Label",
                hintText: "Example: AY 2026-27 Commencement",
                border: OutlineInputBorder(),
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
              ElevatedButton(
                onPressed: () => Navigator.pop(context, labelController.text.trim()),
                child: const Text("Save"),
              ),
            ],
          ),
        );
        if (label == null || label.isEmpty) return;
        try {
          await ApiService.addCommencementDate(date: iso, label: label);
          await loadAll();
        } catch (e) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text("Failed to save commencement date: $e"), backgroundColor: Colors.red),
          );
        }
        break;

      case "remove_commencement":
        try {
          await ApiService.deleteCommencementDate(iso);
          await loadAll();
        } catch (e) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text("Failed to remove commencement date: $e"), backgroundColor: Colors.red),
          );
        }
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final firstDayOfMonth = DateTime(visibleMonth.year, visibleMonth.month, 1);
    final daysInMonth = DateTime(visibleMonth.year, visibleMonth.month + 1, 0).day;
    final leadingEmptyDays = (firstDayOfMonth.weekday - 1) % 7; // Monday-start week
    final today = DateTime.now();

    return Scaffold(
      appBar: AppBar(
        title: const Text("Academic Calendar"),
      ),
      body: Center(
        child: SizedBox(
          width: 650,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(icon: const Icon(Icons.chevron_left), onPressed: () => changeMonth(-1)),
                  Text(
                    "${_monthName(visibleMonth.month)} ${visibleMonth.year}",
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  IconButton(icon: const Icon(Icons.chevron_right), onPressed: () => changeMonth(1)),
                ],
              ),

              const SizedBox(height: 10),

              Wrap(
                spacing: 12,
                runSpacing: 6,
                children: const [
                  _LegendDot(color: Colors.redAccent, label: "Holiday"),
                  _LegendDot(color: Colors.indigo, label: "Scheduled due date"),
                  _LegendDot(color: Colors.green, label: "Commencement"),
                ],
              ),

              const SizedBox(height: 15),

              OutlinedButton.icon(
                onPressed: addIndianHolidays,
                icon: const Icon(Icons.flag),
                label: Text("Add Indian Holidays for ${visibleMonth.year}"),
              ),

              const SizedBox(height: 10),

              ElevatedButton.icon(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const _ScheduleCompletionScreen()),
                  );
                },
                icon: const Icon(Icons.fact_check),
                label: const Text("Check Schedule Completion"),
              ),

              const SizedBox(height: 10),

              OutlinedButton.icon(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const _NamingCheckScreen()),
                  );
                },
                icon: const Icon(Icons.spellcheck),
                label: const Text("Check Naming Mismatches"),
              ),

              const SizedBox(height: 15),

              if (isLoading) const Center(child: CircularProgressIndicator()),

              GridView.count(
                crossAxisCount: 7,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  for (final w in const ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
                    Center(
                      child: Text(w, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
                    ),
                  for (int i = 0; i < leadingEmptyDays; i++) const SizedBox.shrink(),
                  for (int day = 1; day <= daysInMonth; day++)
                    _dayCell(DateTime(visibleMonth.year, visibleMonth.month, day), today),
                ],
              ),

              const SizedBox(height: 20),
              const Divider(),
              const Text("Upcoming Holidays", style: TextStyle(fontWeight: FontWeight.bold)),
              for (final h in holidays.where((h) => (h["date"] as String).compareTo(_iso(today)) >= 0).take(5))
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.circle, size: 10, color: Colors.redAccent),
                  title: Text(h["name"] ?? ""),
                  trailing: Text(h["date"] ?? ""),
                ),

              const SizedBox(height: 10),
              const Text("Upcoming Scheduled Due Dates", style: TextStyle(fontWeight: FontWeight.bold)),
              for (final s in schedule.where((s) => (s["date"] as String).compareTo(_iso(today)) >= 0).take(5))
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.circle, size: 10, color: Colors.indigo),
                  title: Text("Regulation ${s["regulation"]}"),
                  subtitle: Text(_pairsLabel(s)),
                  trailing: Text(s["date"] ?? ""),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _dayCell(DateTime date, DateTime today) {
    final iso = _iso(date);
    final isHoliday = _holidayOn(iso) != null;
    final isScheduled = _scheduleOn(iso) != null;
    final isCommencement = _commencementOn(iso) != null;
    final isToday = _iso(today) == iso;

    Color? fill;
    if (isHoliday) fill = Colors.redAccent.withOpacity(0.15);
    if (isCommencement) fill = Colors.green.withOpacity(0.15);

    return InkWell(
      onTap: () => onDayTap(date),
      child: Container(
        margin: const EdgeInsets.all(2),
        decoration: BoxDecoration(
          color: fill,
          border: isToday ? Border.all(color: Colors.indigo, width: 2) : null,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            Text("${date.day}"),
            if (isScheduled)
              const Positioned(
                bottom: 4,
                child: Icon(Icons.circle, size: 6, color: Colors.indigo),
              ),
          ],
        ),
      ),
    );
  }

  String _monthName(int month) {
    const names = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December",
    ];
    return names[month - 1];
  }
}

class _LegendDot extends StatelessWidget {
  final Color color;
  final String label;

  const _LegendDot({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.circle, size: 10, color: color),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(fontSize: 12)),
      ],
    );
  }
}

// ============================================================
// YEAR + DEPARTMENT PAIR PICKER (shared)
// ============================================================
//
// Used by both the Schedule Editor and Schedule Completion screens.
// Deliberately NOT two separate multi-selects — that shape
// cross-multiplies (Years [III, II] x Departments [CSE, IT] would
// expand to all four combinations instead of just the pairs picked).
// Fully controlled: the parent owns `pairs`.

class _YearDepartmentPairPicker extends StatefulWidget {
  final List<String> years;
  final List<String> departments;
  final List<Map<String, String>> pairs;
  final void Function(String year, String department) onAdd;
  final void Function(Map<String, String> pair) onRemove;

  const _YearDepartmentPairPicker({
    required this.years,
    required this.departments,
    required this.pairs,
    required this.onAdd,
    required this.onRemove,
  });

  @override
  State<_YearDepartmentPairPicker> createState() => _YearDepartmentPairPickerState();
}

class _YearDepartmentPairPickerState extends State<_YearDepartmentPairPicker> {
  static const String _all = "__ALL__";

  String? pickerYear;
  String? pickerDepartment;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("Year + Department Combinations", style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        const Text(
          "Add each Year/Department pair you want — e.g. III + CSE, "
          "then II + IT — rather than picking Years and Departments "
          "separately, which would wrongly combine every Year with "
          "every Department.",
          style: TextStyle(color: Colors.grey, fontSize: 12),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                value: pickerYear,
                decoration: const InputDecoration(labelText: "Year", border: OutlineInputBorder()),
                items: [
                  const DropdownMenuItem(
                    value: _all,
                    child: Text("All Years", style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                  ...widget.years.map((y) => DropdownMenuItem(value: y, child: Text(y))),
                ],
                onChanged: (v) => setState(() => pickerYear = v),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: DropdownButtonFormField<String>(
                value: pickerDepartment,
                decoration: const InputDecoration(labelText: "Department", border: OutlineInputBorder()),
                items: [
                  const DropdownMenuItem(
                    value: _all,
                    child: Text("All Departments", style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                  ...widget.departments.map((d) => DropdownMenuItem(value: d, child: Text(d))),
                ],
                onChanged: (v) => setState(() => pickerDepartment = v),
              ),
            ),
            const SizedBox(width: 10),
            IconButton(
              icon: const Icon(Icons.add_circle, color: Colors.indigo),
              onPressed: () {
                if (pickerYear == null || pickerDepartment == null) return;

                // "All" expands to every known value; duplicates are
                // ignored by the parent's addPair.
                final yearsToAdd = pickerYear == _all ? widget.years : [pickerYear!];
                final deptsToAdd = pickerDepartment == _all ? widget.departments : [pickerDepartment!];

                for (final y in yearsToAdd) {
                  for (final d in deptsToAdd) {
                    widget.onAdd(y, d);
                  }
                }
                setState(() {
                  pickerYear = null;
                  pickerDepartment = null;
                });
              },
            ),
          ],
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: widget.pairs.map((p) {
            return Chip(
              label: Text("${p['year']} + ${p['department']}"),
              onDeleted: () => widget.onRemove(p),
            );
          }).toList(),
        ),
      ],
    );
  }
}

// ============================================================
// SCHEDULE EDITOR — set/edit a due date for Year+Department combos
// ============================================================
//
// Regulation + Year/Department combinations are all that's needed:
// on save, every subject for those combinations is scheduled.

class _ScheduleEditorScreen extends StatefulWidget {
  final String date;
  final Map<String, dynamic>? existing;

  const _ScheduleEditorScreen({required this.date, this.existing});

  @override
  State<_ScheduleEditorScreen> createState() => _ScheduleEditorScreenState();
}

class _ScheduleEditorScreenState extends State<_ScheduleEditorScreen> {
  List<Map<String, dynamic>> regulations = [];
  List<String> allYears = [];
  List<String> allDepartments = [];

  String? selectedRegulation;
  List<Map<String, String>> selectedPairs = [];

  final notesUnitsController = TextEditingController();
  final assignmentUnitsController = TextEditingController();
  final qaUnitsController = TextEditingController();

  bool isLoadingMeta = false;
  bool isSaving = false;

  bool get isEditing => widget.existing != null;

  @override
  void initState() {
    super.initState();
    loadMeta();
  }

  @override
  void dispose() {
    notesUnitsController.dispose();
    assignmentUnitsController.dispose();
    qaUnitsController.dispose();
    super.dispose();
  }

  void addPair(String year, String department) {
    final exists = selectedPairs.any((p) => p["year"] == year && p["department"] == department);
    if (exists) return;
    setState(() {
      selectedPairs = [...selectedPairs, {"year": year, "department": department}];
    });
  }

  void removePair(Map<String, String> pair) {
    setState(() {
      selectedPairs = selectedPairs.where((p) => p != pair).toList();
    });
  }

  // Picking a regulation pre-fills the Year+Department combinations
  // from its setup scope (blank == all), but only when nothing has
  // been chosen yet — it never overwrites combinations already added.
  void onRegulationChanged(String? name) {
    setState(() => selectedRegulation = name);
    if (name == null || selectedPairs.isNotEmpty) return;

    final reg = regulations.firstWhere(
      (r) => r["name"] == name,
      orElse: () => <String, dynamic>{},
    );
    if (reg.isEmpty) return;

    final regYears = ((reg["years"] as List?) ?? []).map((e) => e.toString()).toList();
    final regDepts = ((reg["departments"] as List?) ?? []).map((e) => e.toString()).toList();

    final useYears = regYears.isEmpty ? allYears : regYears;
    final useDepts = regDepts.isEmpty ? allDepartments : regDepts;

    setState(() {
      selectedPairs = [
        for (final y in useYears)
          for (final d in useDepts) {"year": y, "department": d},
      ];
    });
  }

  Future<void> loadMeta() async {
    setState(() => isLoadingMeta = true);
    try {
      final regs = await ApiService.getRegulations();
      final yrs = await ApiService.getYears();
      final depts = await ApiService.getDepartments();
      if (!mounted) return;
      setState(() {
        regulations = regs;
        allYears = yrs;
        allDepartments = depts;
      });

      final existing = widget.existing;
      if (existing != null) {
        final derivedPairs = _pairsOf(existing);

        setState(() {
          selectedRegulation = existing["regulation"];
          selectedPairs = derivedPairs;
          notesUnitsController.text = (existing["notes_required_units"] as List?)?.join(", ") ?? "";
          assignmentUnitsController.text = (existing["assignment_required_units"] as List?)?.join(", ") ?? "";
          qaUnitsController.text = (existing["qa_required_units"] as List?)?.join(", ") ?? "";
        });
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to load setup data: $e"), backgroundColor: Colors.red),
      );
    }
    if (!mounted) return;
    setState(() => isLoadingMeta = false);
  }

  void _error(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  // Saving only stores the date, regulation, Year+Department
  // combinations and requirements — nothing is loaded from Google
  // Classroom here.
  Future<void> save() async {
    if (selectedRegulation == null) {
      _error("Pick a regulation");
      return;
    }
    if (selectedPairs.isEmpty) {
      _error("Add at least one Year + Department combination");
      return;
    }

    setState(() => isSaving = true);
    try {
      await ApiService.saveAcademicSchedule(
        date: widget.date,
        regulation: selectedRegulation!,
        pairs: selectedPairs,
        notesRequiredUnits: _parseNumberList(notesUnitsController.text),
        assignmentRequiredUnits: _parseNumberList(assignmentUnitsController.text),
        qaRequiredUnits: _parseNumberList(qaUnitsController.text),
      );

      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      _error("Failed to save schedule: $e");
      setState(() => isSaving = false);
    }
  }

  Future<void> deleteSchedule() async {
    try {
      await ApiService.deleteAcademicSchedule(widget.date);
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      _error("Failed to delete: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("${isEditing ? 'Edit' : 'Set'} Schedule — ${widget.date}"),
        actions: [
          if (isEditing)
            IconButton(
              tooltip: "Delete Schedule",
              icon: const Icon(Icons.delete),
              onPressed: deleteSchedule,
            ),
        ],
      ),
      body: Center(
        child: SizedBox(
          width: 750,
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              DropdownButtonFormField<String>(
                value: selectedRegulation,
                decoration: InputDecoration(
                  labelText: isLoadingMeta ? "Loading..." : "Regulation",
                  border: const OutlineInputBorder(),
                ),
                items: regulations
                    .map((r) => DropdownMenuItem(value: r["name"].toString(), child: Text(r["name"].toString())))
                    .toList(),
                onChanged: onRegulationChanged,
              ),

              const SizedBox(height: 20),

              _YearDepartmentPairPicker(
                years: allYears,
                departments: allDepartments,
                pairs: selectedPairs,
                onAdd: addPair,
                onRemove: removePair,
              ),

              const SizedBox(height: 25),
              const Divider(),
              const SizedBox(height: 15),

              const Text("Requirements", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 15),

              TextField(
                controller: notesUnitsController,
                decoration: const InputDecoration(
                  labelText: "Notes Required Units",
                  hintText: "Example: unit-1, unit-2",
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 15),
              TextField(
                controller: assignmentUnitsController,
                decoration: const InputDecoration(
                  labelText: "Assignments Required",
                  hintText: "Example: 1, 2",
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 15),
              TextField(
                controller: qaUnitsController,
                decoration: const InputDecoration(
                  labelText: "QA Required Units (all parts of the regulation)",
                  hintText: "Example: unit-1, unit-2",
                  border: OutlineInputBorder(),
                ),
              ),

              const SizedBox(height: 20),

              ElevatedButton.icon(
                onPressed: isSaving ? null : save,
                icon: const Icon(Icons.event_available),
                label: Text(
                  isSaving
                      ? "Saving..."
                      : "Save Schedule (${selectedPairs.length} combination(s))",
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ============================================================
// CHECK SCHEDULE COMPLETION
// ============================================================
//
// Lists the scheduled due dates. Tapping one downloads its Pending
// and Completed Excel sheets — that is the completion check. Google
// Classroom is only read at this point, for the Year+Department
// combinations scheduled on that date.

class _ScheduleCompletionScreen extends StatefulWidget {
  const _ScheduleCompletionScreen();

  @override
  State<_ScheduleCompletionScreen> createState() => _ScheduleCompletionScreenState();
}

class _ScheduleCompletionScreenState extends State<_ScheduleCompletionScreen> {
  List<Map<String, dynamic>> scheduledDates = [];
  bool isLoading = false;
  String? downloadingDate;

  @override
  void initState() {
    super.initState();
    loadSchedule();
  }

  Future<void> loadSchedule() async {
    setState(() => isLoading = true);
    try {
      final data = await ApiService.getAcademicSchedule();
      if (!mounted) return;
      setState(() {
        // Most recent first.
        scheduledDates = [...data]
          ..sort((a, b) => (b["date"] as String).compareTo(a["date"] as String));
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to load due dates: $e"), backgroundColor: Colors.red),
      );
    }
    if (!mounted) return;
    setState(() => isLoading = false);
  }

  Future<void> downloadForDate(Map<String, dynamic> entry) async {
    final date = entry["date"].toString();
    final regulation = entry["regulation"].toString();

    setState(() => downloadingDate = date);
    try {
      await downloadDueDateReports(regulation, date: date);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Pending and Completed reports (Excel and PDF) for $date downloaded")),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to download report: $e"), backgroundColor: Colors.red),
      );
    }
    if (!mounted) return;
    setState(() => downloadingDate = null);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Check Schedule Completion"),
        actions: [
          IconButton(
            tooltip: "Refresh",
            icon: const Icon(Icons.refresh),
            onPressed: isLoading ? null : loadSchedule,
          ),
        ],
      ),
      body: Center(
        child: SizedBox(
          width: 700,
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              const Text(
                "Tap a scheduled due date to download its Pending and "
                "Completed reports as Excel sheets (one sheet per "
                "course) and as PDFs.",
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 16),

              if (isLoading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (scheduledDates.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Text("No due dates scheduled yet.", style: TextStyle(color: Colors.grey.shade600)),
                )
              else
                Card(
                  child: Column(
                    children: [
                      for (final entry in scheduledDates)
                        ListTile(
                          leading: const Icon(Icons.event, color: Colors.indigo),
                          title: Text("${entry["date"]} — Regulation ${entry["regulation"]}"),
                          subtitle: Text(_pairsLabel(entry)),
                          trailing: downloadingDate == entry["date"]
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.download, color: Colors.indigo),
                          onTap: downloadingDate != null ? null : () => downloadForDate(entry),
                        ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

// ============================================================
// NAMING MISMATCHES
// ============================================================
//
// Pick Year + Department combinations and download a report of every
// uploaded item whose title doesn't follow the standard naming
// format — grouped by department, then course — as Excel or PDF.
// Google Classroom is read only when a button is pressed.

class _NamingCheckScreen extends StatefulWidget {
  const _NamingCheckScreen();

  @override
  State<_NamingCheckScreen> createState() => _NamingCheckScreenState();
}

class _NamingCheckScreenState extends State<_NamingCheckScreen> {
  List<String> allYears = [];
  List<String> allDepartments = [];
  List<Map<String, String>> selectedPairs = [];

  bool isLoadingMeta = false;
  String? downloadingFormat; // "xlsx" or "pdf" while a download runs

  @override
  void initState() {
    super.initState();
    loadMeta();
  }

  Future<void> loadMeta() async {
    setState(() => isLoadingMeta = true);
    try {
      final yrs = await ApiService.getYears();
      final depts = await ApiService.getDepartments();
      if (!mounted) return;
      setState(() {
        allYears = yrs;
        allDepartments = depts;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to load years/departments: $e"), backgroundColor: Colors.red),
      );
    }
    if (!mounted) return;
    setState(() => isLoadingMeta = false);
  }

  void addPair(String year, String department) {
    final exists = selectedPairs.any((p) => p["year"] == year && p["department"] == department);
    if (exists) return;
    setState(() {
      selectedPairs = [...selectedPairs, {"year": year, "department": department}];
    });
  }

  void removePair(Map<String, String> pair) {
    setState(() {
      selectedPairs = selectedPairs.where((p) => p != pair).toList();
    });
  }

  Future<void> download(String format) async {
    if (selectedPairs.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Add at least one Year + Department combination"),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => downloadingFormat = format);
    try {
      await downloadNamingMismatches(selectedPairs, format: format);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Naming mismatch report (${format.toUpperCase()}) downloaded")),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to download report: $e"), backgroundColor: Colors.red),
      );
    }
    if (!mounted) return;
    setState(() => downloadingFormat = null);
  }

  @override
  Widget build(BuildContext context) {
    final busy = downloadingFormat != null;

    return Scaffold(
      appBar: AppBar(title: const Text("Check Naming Mismatches")),
      body: Center(
        child: SizedBox(
          width: 700,
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              const Text(
                "Finds uploads in Google Classroom whose names are not in "
                "the standard format (for example 'Chapter 3' instead of "
                "'Unit-3', or a QA title with no Part), for every section "
                "of the chosen years and departments. The report is "
                "grouped by department, then course.",
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 12),
              const Text("Standard names", style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              const Text("Notes:  Unit 1  /  Unit-1"),
              const Text("Assignment:  Assignment-1  /  Assignment 1  /  Unit-1 Assignment"),
              const Text("QA:  Unit-1 Part-A Q&A  (Part A is also accepted)"),
              const Text("Capital, small and sentence case are all accepted."),

              const SizedBox(height: 20),

              if (isLoadingMeta)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Center(child: CircularProgressIndicator()),
                )
              else
                _YearDepartmentPairPicker(
                  years: allYears,
                  departments: allDepartments,
                  pairs: selectedPairs,
                  onAdd: addPair,
                  onRemove: removePair,
                ),

              const SizedBox(height: 20),

              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: busy ? null : () => download("xlsx"),
                      icon: const Icon(Icons.table_chart),
                      label: Text(downloadingFormat == "xlsx" ? "Downloading..." : "Download Excel"),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: busy ? null : () => download("pdf"),
                      icon: const Icon(Icons.picture_as_pdf),
                      label: Text(downloadingFormat == "pdf" ? "Downloading..." : "Download PDF"),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}