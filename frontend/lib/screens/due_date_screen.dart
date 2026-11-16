import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/report_downloader.dart';

class DueDateScreen extends StatefulWidget {
  const DueDateScreen({super.key});

  @override
  State<DueDateScreen> createState() => _DueDateScreenState();
}

class _DueDateScreenState extends State<DueDateScreen> {
  List<Map<String, dynamic>> regulations = [];
  String? selectedRegulation;

  bool isLoadingRegulations = false;
  bool isDownloading = false;

  @override
  void initState() {
    super.initState();
    loadRegulations();
  }

  // Load Regulation Templates
  Future<void> loadRegulations() async {
    setState(() => isLoadingRegulations = true);

    try {
      final data = await ApiService.getRegulations();
      if (!mounted) return;
      setState(() {
        regulations = data;
        // If the previously-selected regulation no longer exists
        // (e.g. renamed), fall back to nothing selected.
        if (!regulations.any((r) => r["name"] == selectedRegulation)) {
          selectedRegulation = null;
        }
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Failed to load regulations: $e"),
          backgroundColor: Colors.red,
        ),
      );
    }

    if (!mounted) return;
    setState(() => isLoadingRegulations = false);
  }

  Map<String, dynamic>? get selectedRegulationData {
    if (selectedRegulation == null) return null;
    for (final r in regulations) {
      if (r["name"] == selectedRegulation) return r;
    }
    return null;
  }

  String formatDate(String? iso) {
    if (iso == null || iso.isEmpty) return "Not set";
    final date = DateTime.tryParse(iso);
    if (date == null) return "Not set";
    return "${date.day.toString().padLeft(2, '0')}-"
        "${date.month.toString().padLeft(2, '0')}-"
        "${date.year}";
  }

  // Create New Regulation
  Future<void> createRegulation() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => const RegulationEditorDialog(),
    );

    if (result == null) return;
    await submitRegulation(result);
  }

  // Edit Selected Regulation
  Future<void> editRegulation() async {
    final existing = selectedRegulationData;

    if (existing == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Select a regulation first"),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => RegulationEditorDialog(existing: existing),
    );

    if (result == null) return;
    await submitRegulation(result, keepSelectionName: result["name"]);
  }

  Future<void> submitRegulation(
    Map<String, dynamic> result, {
    String? keepSelectionName,
  }) async {
    try {
      await ApiService.saveRegulation(
        name: result["name"],
        qaParts: List<Map<String, String>>.from(result["qa_parts"]),
        years: List<String>.from(result["years"]),
        departments: List<String>.from(result["departments"]),
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Regulation saved")),
      );

      await loadRegulations();

      if (!mounted) return;
      setState(() {
        selectedRegulation = keepSelectionName ?? result["name"];
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Failed to save regulation: $e"),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  // Download Due Date Reports — Pending and Completed workbooks,
  // one sheet per course, limited to the regulation's scope.
  Future<void> downloadReport() async {
    if (selectedRegulation == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Select a regulation first"),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => isDownloading = true);

    try {
      await downloadDueDateReports(selectedRegulation!);

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Pending and Completed reports downloaded")),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Failed to download report: $e"),
          backgroundColor: Colors.red,
        ),
      );
    }

    if (!mounted) return;
    setState(() => isDownloading = false);
  }

  @override
  Widget build(BuildContext context) {
    final data = selectedRegulationData;

    return Scaffold(
      appBar: AppBar(
        title: const Text("Due Date Management"),
      ),
      body: Center(
        child: SizedBox(
          width: 650,
          child: ListView(
            padding: const EdgeInsets.all(30),
            children: [
              const Text(
                "Due Date Management",
                style: TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                "Each regulation has a scope (years and departments). "
                "The completion check and the Excel reports only look at "
                "that scope.",
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 25),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: selectedRegulation,
                      decoration: InputDecoration(
                        labelText: isLoadingRegulations
                            ? "Loading regulations..."
                            : "Regulation",
                        border: const OutlineInputBorder(),
                      ),
                      items: regulations
                          .map(
                            (r) => DropdownMenuItem(
                              value: r["name"].toString(),
                              child: Text(r["name"].toString()),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        setState(() => selectedRegulation = value);
                      },
                    ),
                  ),
                  const SizedBox(width: 10),
                  IconButton(
                    tooltip: "Edit Selected Regulation",
                    icon: const Icon(Icons.edit, color: Colors.indigo),
                    onPressed: editRegulation,
                  ),
                  IconButton(
                    tooltip: "Create New Regulation",
                    icon: const Icon(Icons.add_circle, color: Colors.indigo),
                    onPressed: createRegulation,
                  ),
                ],
              ),
              if (data != null) ...[
                const SizedBox(height: 20),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _summaryRow(
                          "Years",
                          (data["years"] as List?)?.isNotEmpty == true
                              ? (data["years"] as List).join(", ")
                              : "All years",
                        ),
                        _summaryRow(
                          "Departments",
                          (data["departments"] as List?)?.isNotEmpty == true
                              ? (data["departments"] as List).join(", ")
                              : "All departments",
                        ),
                        _summaryRow("Due Date", formatDate(data["due_date"])),
                        _summaryRow(
                          "Notes Required Units",
                          (data["notes_required_units"] as List?)
                                  ?.join(", ") ??
                              "-",
                        ),
                        _summaryRow(
                          "Assignments Required",
                          (data["assignment_required_units"] as List?)
                                  ?.join(", ") ??
                              "-",
                        ),
                        _summaryRow(
                          "QA Required Units",
                          (data["qa_required_units"] as List?)?.join(", ") ??
                              "-",
                        ),
                        _summaryRow(
                          "QA Parts",
                          (data["qa_parts"] as List?)
                                  ?.map((p) => "${p["part"]} (${p["type"]})")
                                  .join(", ") ??
                              "-",
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 30),
              ElevatedButton.icon(
                onPressed: isDownloading ? null : downloadReport,
                icon: const Icon(Icons.download),
                label: Text(
                  isDownloading
                      ? "Downloading..."
                      : "Download Due Date Report",
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _summaryRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 180,
            child: Text(label, style: const TextStyle(color: Colors.grey)),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================
// REGULATION EDITOR DIALOG
// ============================================================
//
// Handles BOTH creating a new regulation and editing an existing one
// (pass `existing` to pre-fill). Years and Departments are picked from
// the lists the server knows about, with "All" checkboxes. "All" is
// saved as an empty list, which the backend already treats as
// "no restriction".

class RegulationEditorDialog extends StatefulWidget {
  final Map<String, dynamic>? existing;

  const RegulationEditorDialog({super.key, this.existing});

  @override
  State<RegulationEditorDialog> createState() =>
      _RegulationEditorDialogState();
}

class _RegulationEditorDialogState extends State<RegulationEditorDialog> {
  late final nameController = TextEditingController(
    text: widget.existing?["name"]?.toString() ?? "",
  );
  late final notesUnitsController = TextEditingController(
    text: (widget.existing?["notes_required_units"] as List?)?.join(", ") ?? "",
  );
  late final assignmentUnitsController = TextEditingController(
    text: (widget.existing?["assignment_required_units"] as List?)?.join(", ") ?? "",
  );
  late final qaUnitsController = TextEditingController(
    text: (widget.existing?["qa_required_units"] as List?)?.join(", ") ?? "",
  );

  // ---- Year / Department scope ----
  List<String> availableYears = [];
  List<String> availableDepartments = [];
  bool isLoadingOptions = true;
  String? optionsError;

  late final Set<String> selectedYears =
      ((widget.existing?["years"] as List?) ?? [])
          .map((e) => e.toString())
          .toSet();
  late final Set<String> selectedDepartments =
      ((widget.existing?["departments"] as List?) ?? [])
          .map((e) => e.toString())
          .toSet();

  // Empty saved list == "all".
  late bool allYears = selectedYears.isEmpty;
  late bool allDepartments = selectedDepartments.isEmpty;

  late DateTime? dueDate = widget.existing?["due_date"] != null
      ? DateTime.tryParse(widget.existing!["due_date"].toString())
      : null;

  late final List<_QaPartRow> rows = (() {
    final existingParts = widget.existing?["qa_parts"] as List?;
    if (existingParts == null || existingParts.isEmpty) {
      return [_QaPartRow()];
    }
    return existingParts
        .map(
          (p) => _QaPartRow(
            part: p["part"]?.toString() ?? "",
            type: p["type"]?.toString() ?? "Q&A",
          ),
        )
        .toList();
  })();

  bool get isEditing => widget.existing != null;

  @override
  void initState() {
    super.initState();
    loadOptions();
  }

  @override
  void dispose() {
    nameController.dispose();
    notesUnitsController.dispose();
    assignmentUnitsController.dispose();
    qaUnitsController.dispose();
    for (final row in rows) {
      row.partController.dispose();
    }
    super.dispose();
  }

  Future<void> loadOptions() async {
    try {
      final data = await ApiService.fetchFilters();
      if (!mounted) return;
      setState(() {
        availableYears = List<String>.from(data["years"]);
        availableDepartments = List<String>.from(data["departments"]);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => optionsError = "Couldn't load years/departments: $e");
    }
    if (!mounted) return;
    setState(() => isLoadingOptions = false);
  }

  // Server options plus any previously-saved value that no longer
  // appears in the server list, so editing never silently drops it.
  List<String> _optionsWith(List<String> available, Set<String> selected) {
    return [...available, ...selected.where((s) => !available.contains(s))];
  }

  Widget _scopePicker({
    required String title,
    required String allLabel,
    required bool all,
    required ValueChanged<bool> onAllChanged,
    required List<String> options,
    required Set<String> selected,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          dense: true,
          controlAffinity: ListTileControlAffinity.leading,
          title: Text(allLabel),
          value: all,
          onChanged: (v) => onAllChanged(v ?? false),
        ),
        if (!all)
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              for (final option in options)
                FilterChip(
                  label: Text(option),
                  selected: selected.contains(option),
                  onSelected: (isOn) {
                    setState(() {
                      if (isOn) {
                        selected.add(option);
                      } else {
                        selected.remove(option);
                      }
                    });
                  },
                ),
            ],
          ),
      ],
    );
  }

  void addRow() {
    setState(() => rows.add(_QaPartRow()));
  }

  void removeRow(int index) {
    setState(() => rows.removeAt(index));
  }

  Future<void> pickDueDate() async {
    final date = await showDatePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime(2050),
      initialDate: dueDate ?? DateTime.now(),
    );

    if (date == null) return;

    setState(() => dueDate = date);
  }

  String formatDueDate() {
    if (dueDate == null) return "Select date";
    return "${dueDate!.day.toString().padLeft(2, '0')}-"
        "${dueDate!.month.toString().padLeft(2, '0')}-"
        "${dueDate!.year}";
  }

  String? isoDueDate() {
    if (dueDate == null) return null;
    return "${dueDate!.year.toString().padLeft(4, '0')}-"
        "${dueDate!.month.toString().padLeft(2, '0')}-"
        "${dueDate!.day.toString().padLeft(2, '0')}";
  }

  // "unit-1, Unit 2, 3" -> [1, 2, 3] — pulls the first number out of
  // each comma-separated piece. Pieces with no number are skipped.
  List<int> parseNumberList(String text) {
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

  void _error(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  void save() {
    final name = nameController.text.trim();

    if (name.isEmpty) {
      _error("Regulation name is required");
      return;
    }

    if (!allYears && selectedYears.isEmpty) {
      _error("Pick at least one year, or tick All years");
      return;
    }

    if (!allDepartments && selectedDepartments.isEmpty) {
      _error("Pick at least one department, or tick All departments");
      return;
    }

    final qaParts = rows
        .where((row) => row.partController.text.trim().isNotEmpty)
        .map(
          (row) => {
            "part": row.partController.text.trim().toUpperCase(),
            "type": row.type,
          },
        )
        .toList();

    if (qaParts.isEmpty) {
      _error("Add at least one Part");
      return;
    }

    Navigator.pop(context, {
      "name": name,
      "qa_parts": qaParts,
      "due_date": isoDueDate(),
      "notes_required_units": parseNumberList(notesUnitsController.text),
      "assignment_required_units":
          parseNumberList(assignmentUnitsController.text),
      "qa_required_units": parseNumberList(qaUnitsController.text),
      // Empty list == applies to all.
      "years": allYears ? <String>[] : selectedYears.toList(),
      "departments":
          allDepartments ? <String>[] : selectedDepartments.toList(),
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(isEditing ? "Edit Regulation" : "New Regulation"),
      content: SizedBox(
        width: 500,
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(
                  labelText: "Regulation Name",
                  hintText: "Example: 2025",
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 20),
              const Text(
                "Applies To",
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 4),
              const Text(
                "Tick All to apply to every year or department, or pick "
                "specific ones. The completion check and Excel reports "
                "only cover this scope.",
                style: TextStyle(color: Colors.grey, fontSize: 12),
              ),
              const SizedBox(height: 10),
              if (isLoadingOptions)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: LinearProgressIndicator(),
                )
              else ...[
                if (optionsError != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      optionsError!,
                      style: const TextStyle(color: Colors.red, fontSize: 12),
                    ),
                  ),
                _scopePicker(
                  title: "Years",
                  allLabel: "All years",
                  all: allYears,
                  onAllChanged: (v) => setState(() => allYears = v),
                  options: _optionsWith(availableYears, selectedYears),
                  selected: selectedYears,
                ),
                const SizedBox(height: 10),
                _scopePicker(
                  title: "Departments",
                  allLabel: "All departments",
                  all: allDepartments,
                  onAllChanged: (v) => setState(() => allDepartments = v),
                  options:
                      _optionsWith(availableDepartments, selectedDepartments),
                  selected: selectedDepartments,
                ),
              ],
              const SizedBox(height: 20),
              const Text(
                "Common Due Date",
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 4),
              const Text(
                "Applies to Notes, Assignments, and QA for every "
                "course evaluated against this regulation.",
                style: TextStyle(color: Colors.grey, fontSize: 12),
              ),
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: pickDueDate,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text("Due Date"),
                      Text(
                        formatDueDate(),
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),
              const Text(
                "Requirements",
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 4),
              const Text(
                "Explicit numbers, not counts — accepts \"unit-1\", "
                "\"Unit 1\", or plain \"1\" alike.",
                style: TextStyle(color: Colors.grey, fontSize: 12),
              ),
              const SizedBox(height: 10),
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
                  labelText: "QA Required Units (all parts below)",
                  hintText: "Example: unit-1, unit-2",
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 20),
              const Text(
                "QA Parts (applied to every required unit)",
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              ...rows.asMap().entries.map((entry) {
                final index = entry.key;
                final row = entry.value;

                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 90,
                        child: TextField(
                          controller: row.partController,
                          decoration: const InputDecoration(
                            labelText: "Part",
                            hintText: "A",
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: StatefulBuilder(
                          builder: (context, setRowState) {
                            return DropdownButtonFormField<String>(
                              value: row.type,
                              decoration: const InputDecoration(
                                labelText: "Type",
                                border: OutlineInputBorder(),
                              ),
                              items: const [
                                DropdownMenuItem(
                                  value: "Q&A",
                                  child: Text("Q&A"),
                                ),
                                DropdownMenuItem(
                                  value: "MCQ Q&A",
                                  child: Text("MCQ Q&A"),
                                ),
                              ],
                              onChanged: (value) {
                                setRowState(() {
                                  row.type = value ?? "Q&A";
                                });
                              },
                            );
                          },
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.remove_circle,
                            color: Colors.red),
                        onPressed:
                            rows.length > 1 ? () => removeRow(index) : null,
                      ),
                    ],
                  ),
                );
              }),
              TextButton.icon(
                onPressed: addRow,
                icon: const Icon(Icons.add),
                label: const Text("Add Part"),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text("Cancel"),
        ),
        ElevatedButton(
          onPressed: save,
          child: const Text("Save"),
        ),
      ],
    );
  }
}

class _QaPartRow {
  final partController = TextEditingController();
  String type;

  _QaPartRow({String part = "", this.type = "Q&A"}) {
    partController.text = part;
  }
}