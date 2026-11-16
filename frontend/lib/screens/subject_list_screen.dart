import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class SubjectsListScreen extends StatefulWidget {
  const SubjectsListScreen({super.key});

  @override
  State<SubjectsListScreen> createState() => _SubjectsListScreenState();
}

class _SubjectsListScreenState extends State<SubjectsListScreen> {
  List<String> years = [];
  List<String> departments = [];

  String? selectedYear;
  String? selectedDepartment;

  List<Map<String, dynamic>> subjects = [];

  bool isLoadingMeta = false;
  bool isLoadingSubjects = false;

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
      setState(() {
        years = yrs;
        departments = depts;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Failed to load Years/Departments: $e"),
          backgroundColor: Colors.red,
        ),
      );
    }
    setState(() => isLoadingMeta = false);
  }

  Future<void> loadSubjects() async {
    if (selectedYear == null || selectedDepartment == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Pick both Year and Department"),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => isLoadingSubjects = true);

    try {
      final data = await ApiService.getSubjectUnitCounts(
        pairs: [
          {"year": selectedYear!, "department": selectedDepartment!},
        ],
      );
      setState(() => subjects = data);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Failed to load subjects: $e"),
          backgroundColor: Colors.red,
        ),
      );
    }

    setState(() => isLoadingSubjects = false);
  }

  Future<void> editUnitCount(Map<String, dynamic> subject) async {
    final controller = TextEditingController(
      text: subject["unit_count"]?.toString() ?? "",
    );

    final result = await showDialog<int>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text("Unit Count — ${subject["subject"]}"),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          autofocus: true,
          decoration: const InputDecoration(
            labelText: "Unit Count",
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Cancel"),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, int.tryParse(controller.text.trim())),
            child: const Text("Save"),
          ),
        ],
      ),
    );

    if (result == null) return;

    try {
      await ApiService.setSubjectUnitOverride(
        year: selectedYear!,
        department: selectedDepartment!,
        subject: subject["subject"].toString(),
        unitCount: result,
      );

      // Update the on-screen list immediately rather than waiting on
      // a full reload — same bucket thresholds the backend uses.
      final bucket = result == 5
          ? "5 units"
          : (result < 5 ? "Less than 5 units" : "Greater than 5 units");

      setState(() {
        final index = subjects.indexWhere((s) => s["subject"] == subject["subject"]);
        if (index != -1) {
          subjects[index] = {
            ...subjects[index],
            "unit_count": result,
            "bucket": bucket,
            "overridden": true,
          };
        }
      });

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Unit count updated")),
      );

      // Reconcile with the server in the background — doesn't block
      // the display, which already reflects the change above.
      unawaited(loadSubjects());
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Failed to update: $e"),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  // Summarizes every section teaching this subject, e.g.
  // "A (Dr. Rao), B (Dr. Iyer)" — since a subject is now shown once
  // per Year+Department rather than once per section.
  String _sectionsSummary(dynamic sections) {
    if (sections is! List || sections.isEmpty) return "-";
    return sections
        .map((s) => "${s["section"] ?? "?"} (${s["staff_name"] ?? "-"})")
        .join(", ");
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Subjects List")),
      body: Center(
        child: SizedBox(
          width: 700,
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              const Text(
                "Subject names always come from Google Classroom. Unit "
                "count is auto-detected from uploads, but you can "
                "correct it here if you know the real syllabus "
                "structure.",
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 20),

              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: selectedYear,
                      decoration: InputDecoration(
                        labelText: isLoadingMeta ? "Loading..." : "Year",
                        border: const OutlineInputBorder(),
                      ),
                      items: years
                          .map((y) => DropdownMenuItem(value: y, child: Text(y)))
                          .toList(),
                      onChanged: (v) => setState(() => selectedYear = v),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: selectedDepartment,
                      decoration: InputDecoration(
                        labelText: isLoadingMeta ? "Loading..." : "Department",
                        border: const OutlineInputBorder(),
                      ),
                      items: departments
                          .map((d) => DropdownMenuItem(value: d, child: Text(d)))
                          .toList(),
                      onChanged: (v) => setState(() => selectedDepartment = v),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 15),

              ElevatedButton.icon(
                onPressed: isLoadingSubjects ? null : loadSubjects,
                icon: const Icon(Icons.search),
                label: Text(isLoadingSubjects ? "Loading..." : "Load Subjects"),
              ),

              if (subjects.isNotEmpty) ...[
                const SizedBox(height: 20),
                const Divider(),
                for (final s in subjects)
                  Card(
                    child: ListTile(
                      title: Text(s["subject"]?.toString() ?? ""),
                      subtitle: Text(
                        "${_sectionsSummary(s["sections"])}\n"
                        "Bucket: ${s["bucket"] ?? ""}"
                        "${s["overridden"] == true ? " (manually set)" : " (auto-detected)"}",
                      ),
                      isThreeLine: true,
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            "${s["unit_count"]}",
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.edit, color: Colors.indigo),
                            onPressed: () => editUnitCount(s),
                          ),
                        ],
                      ),
                    ),
                  ),
              ] else if (!isLoadingSubjects) ...[
                const SizedBox(height: 30),
                Center(
                  child: Text(
                    "Pick a Year and Department, then Load Subjects.",
                    style: TextStyle(color: Colors.grey.shade600),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}