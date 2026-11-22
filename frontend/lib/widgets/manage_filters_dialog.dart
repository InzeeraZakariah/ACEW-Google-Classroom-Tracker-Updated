import 'package:flutter/material.dart';
import '../services/api_service.dart';

// Opened from the home screen: add or remove the Departments, Years
// and Sections that appear in the filter dropdowns. The server
// validates every value (roman-numeral years I–X, 1–3 character
// sections, department names without spaces/commas/colons) and its
// message is shown as-is.
class ManageFiltersDialog extends StatefulWidget {
  const ManageFiltersDialog({super.key});

  @override
  State<ManageFiltersDialog> createState() => _ManageFiltersDialogState();
}

class _ManageFiltersDialogState extends State<ManageFiltersDialog> {
  static const List<String> kinds = ["departments", "years", "sections"];
  static const Map<String, String> titles = {
    "departments": "Departments",
    "years": "Years",
    "sections": "Sections",
  };
  static const Map<String, String> fieldLabels = {
    "departments": "New department (e.g. MECH)",
    "years": "New year (e.g. V)",
    "sections": "New section (e.g. E)",
  };

  Map<String, List<String>> filters = {for (final k in kinds) k: []};
  final Map<String, TextEditingController> controllers = {
    for (final k in kinds) k: TextEditingController(),
  };

  bool isLoading = false;
  String? busyKind;
  String? errorMessage; // shown inside the dialog — a snackbar would sit behind it

  @override
  void initState() {
    super.initState();
    load();
  }

  @override
  void dispose() {
    for (final c in controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  void _showError(String message) {
    setState(() => errorMessage = message.replaceFirst("Exception: ", ""));
  }

  void _apply(Map<String, dynamic> data) {
    setState(() {
      errorMessage = null;
      filters = {for (final k in kinds) k: List<String>.from(data[k] ?? [])};
    });
  }

  Future<void> load() async {
    setState(() => isLoading = true);
    try {
      final data = await ApiService.fetchFilters();
      if (!mounted) return;
      _apply(data);
    } catch (e) {
      if (!mounted) return;
      _showError("Failed to load: $e");
    }
    if (mounted) setState(() => isLoading = false);
  }

  Future<void> add(String kind) async {
    final value = controllers[kind]!.text.trim();
    if (value.isEmpty) return;

    setState(() => busyKind = kind);
    try {
      final data = await ApiService.addFilterOption(kind, value);
      if (!mounted) return;
      controllers[kind]!.clear();
      _apply(data);
    } catch (e) {
      if (!mounted) return;
      _showError("$e");
    }
    if (mounted) setState(() => busyKind = null);
  }

  Future<void> remove(String kind, String value) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text("Remove $value?"),
        content: const Text(
          "Removes it from the dropdowns. Saved due-date schedules, "
          "regulations and Google Classroom courses that mention it "
          "are not changed.",
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text("Cancel")),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text("Remove"),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    setState(() => busyKind = kind);
    try {
      final data = await ApiService.removeFilterOption(kind, value);
      if (!mounted) return;
      _apply(data);
    } catch (e) {
      if (!mounted) return;
      _showError("$e");
    }
    if (mounted) setState(() => busyKind = null);
  }

  Widget _section(String kind) {
    final values = filters[kind] ?? [];

    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("${titles[kind]} (${values.length})", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: values
                .map((v) => Chip(
                      label: Text(v),
                      onDeleted: busyKind == null ? () => remove(kind, v) : null,
                    ))
                .toList(),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: controllers[kind],
                  textCapitalization: TextCapitalization.characters,
                  onSubmitted: (_) => add(kind),
                  decoration: InputDecoration(
                    labelText: fieldLabels[kind],
                    isDense: true,
                    border: const OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              ElevatedButton.icon(
                onPressed: busyKind == null ? () => add(kind) : null,
                icon: const Icon(Icons.add),
                label: const Text("Add"),
              ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text("Departments, Years & Sections"),
      content: SizedBox(
        width: 520,
        child: isLoading
            ? const SizedBox(height: 120, child: Center(child: CircularProgressIndicator()))
            : SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (errorMessage != null)
                      Container(
                        width: double.infinity,
                        margin: const EdgeInsets.only(bottom: 16),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: Colors.red.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(errorMessage!, style: const TextStyle(color: Colors.red)),
                      ),
                    for (final kind in kinds) _section(kind),
                  ],
                ),
              ),
      ),
      actions: [
        ElevatedButton(onPressed: () => Navigator.pop(context), child: const Text("Done")),
      ],
    );
  }
}