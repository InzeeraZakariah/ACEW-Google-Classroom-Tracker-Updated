import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/report_downloader.dart';

class RegulationSetupScreen extends StatefulWidget {
  const RegulationSetupScreen({super.key});

  @override
  State<RegulationSetupScreen> createState() => _RegulationSetupScreenState();
}

class _RegulationSetupScreenState extends State<RegulationSetupScreen> {
  List<Map<String, dynamic>> regulations = [];
  String? selectedRegulation;

  bool isLoadingRegulations = false;
  bool isDownloading = false;

  @override
  void initState() {
    super.initState();
    loadRegulations();
  }

  Future<void> loadRegulations() async {
    setState(() => isLoadingRegulations = true);

    try {
      final data = await ApiService.getRegulations();
      setState(() {
        regulations = data;
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

    setState(() => isLoadingRegulations = false);
  }

  Map<String, dynamic>? get selectedRegulationData {
    if (selectedRegulation == null) return null;
    for (final r in regulations) {
      if (r["name"] == selectedRegulation) return r;
    }
    return null;
  }

  Future<void> createRegulation() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => const RegulationEditorDialog(),
    );

    if (result == null) return;
    await submitRegulation(result);
  }

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

  Future<void> deleteRegulation() async {
    if (selectedRegulation == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Select a regulation first"),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text("Delete \"$selectedRegulation\"?"),
        content: const Text(
          "This removes the regulation itself. Any subjects already "
          "scheduled against it (due dates, requirements) are left "
          "as-is — they just won't match anything in reports anymore, "
          "since the regulation they reference no longer exists.",
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text("Cancel"),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text("Delete"),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await ApiService.deleteRegulation(selectedRegulation!);

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Regulation deleted")),
      );

      setState(() => selectedRegulation = null);
      await loadRegulations();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Failed to delete regulation: $e"),
          backgroundColor: Colors.red,
        ),
      );
    }
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

  // Download Due Date Report — one workbook, one row per subject that
  // has a due date scheduled (via the Academic Calendar) against this
  // regulation.
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
      // Two workbooks — Pending and Completed — one sheet per course.
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

    setState(() => isDownloading = false);
  }

  @override
  Widget build(BuildContext context) {
    final data = selectedRegulationData;

    return Scaffold(
      appBar: AppBar(title: const Text("Regulation Setup")),
      body: Center(
        child: SizedBox(
          width: 650,
          child: ListView(
            padding: const EdgeInsets.all(30),
            children: [
              const Text(
                "Regulation Setup",
                style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
              ),

              const SizedBox(height: 8),

              const Text(
                "A regulation defines the QA Part/Type structure and "
                "which Years/Departments it applies to (e.g. a 2025 "
                "regulation for Years I-II, CSE/IT). Due dates aren't "
                "set here — they're scheduled from the Academic "
                "Calendar, since a due date applies to whichever "
                "subjects the dean picks on a given date.",
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
                    tooltip: "Delete Selected Regulation",
                    icon: const Icon(Icons.delete, color: Colors.red),
                    onPressed: deleteRegulation,
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

              const SizedBox(height: 25),

              ElevatedButton.icon(
                onPressed: isDownloading ? null : downloadReport,
                icon: const Icon(Icons.download),
                label: Text(
                  isDownloading
                      ? "Downloading..."
                      : "Download Due Date Report",
                ),
              ),

              const SizedBox(height: 10),

              Text(
                "Due dates and requirements for this regulation are "
                "set from the Academic Calendar screen.",
                style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
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
            width: 150,
            child: Text(label, style: const TextStyle(color: Colors.grey)),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
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
// Creates or edits a regulation: name, Years/Departments scope, and
// QA Part/Type structure. No due date — that's set exclusively from
// the Academic Calendar.

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
  late final yearsController = TextEditingController(
    text: (widget.existing?["years"] as List?)?.join(", ") ?? "",
  );
  late final departmentsController = TextEditingController(
    text: (widget.existing?["departments"] as List?)?.join(", ") ?? "",
  );

  late final List<QaPartRow> rows = (() {
    final existingParts = widget.existing?["qa_parts"] as List?;
    if (existingParts == null || existingParts.isEmpty) {
      return [QaPartRow()];
    }
    return existingParts
        .map(
          (p) => QaPartRow(
            part: p["part"]?.toString() ?? "",
            type: p["type"]?.toString() ?? "Q&A",
          ),
        )
        .toList();
  })();

  bool get isEditing => widget.existing != null;

  void addRow() {
    setState(() => rows.add(QaPartRow()));
  }

  void removeRow(int index) {
    setState(() => rows.removeAt(index));
  }

  // "CSE, IT" -> ["CSE", "IT"] — tolerant comma-splitting.
  List<String> parseTextList(String text) {
    return text
        .split(",")
        .map((piece) => piece.trim())
        .where((piece) => piece.isNotEmpty)
        .toList();
  }

  void save() {
    final name = nameController.text.trim();

    if (name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Regulation name is required"),
          backgroundColor: Colors.red,
        ),
      );
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
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Add at least one Part"),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    Navigator.pop(context, {
      "name": name,
      "qa_parts": qaParts,
      "years": parseTextList(yearsController.text),
      "departments": parseTextList(departmentsController.text),
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
                "Leave blank to apply to every year or department.",
                style: TextStyle(color: Colors.grey, fontSize: 12),
              ),
              const SizedBox(height: 10),

              TextField(
                controller: yearsController,
                decoration: const InputDecoration(
                  labelText: "Years",
                  hintText: "Example: I, II",
                  border: OutlineInputBorder(),
                ),
              ),

              const SizedBox(height: 15),

              TextField(
                controller: departmentsController,
                decoration: const InputDecoration(
                  labelText: "Departments",
                  hintText: "Example: CSE, IT",
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
                        icon: const Icon(Icons.remove_circle, color: Colors.red),
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

class QaPartRow {
  final partController = TextEditingController();
  String type;

  QaPartRow({String part = "", this.type = "Q&A"}) {
    partController.text = part;
  }
}

// "unit-1, Unit 2, 3" -> [1, 2, 3] — pulls the first number out of
// each comma-separated piece, so it accepts "unit-1", "Unit 1", "1",
// or "Assignment 1" alike. Pieces with no number are skipped. Shared
// with academic_calendar_screen.dart.
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