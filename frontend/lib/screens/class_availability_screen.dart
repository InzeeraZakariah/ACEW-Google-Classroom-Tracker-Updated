import 'dart:typed_data';
import 'package:file_saver/file_saver.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

const String _all = "All";

// Two ways to check classes against Google Classroom:
//
//  1. Pick Year / Department / Section ("All" = every value) and
//     download the classes that ARE in Google Classroom as a PDF.
//  2. Paste a class list (Year, Department, Section — e.g. columns
//     copied from Excel) and download the listed classes that are NOT
//     in Google Classroom as a PDF.
class ClassAvailabilityScreen extends StatefulWidget {
  const ClassAvailabilityScreen({super.key});

  @override
  State<ClassAvailabilityScreen> createState() => _ClassAvailabilityScreenState();
}

class _ClassAvailabilityScreenState extends State<ClassAvailabilityScreen> {
  // ---- option 1: dropdown check ----
  List<String> years = [];
  List<String> departments = [];
  List<String> sections = [];

  String selectedYear = _all;
  String selectedDepartment = _all;
  String selectedSection = _all;

  Map<String, dynamic>? result; // last check; cleared when a filter changes

  bool isLoadingFilters = false;
  bool isChecking = false;
  bool isDownloading = false;

  // ---- option 2: pasted class list ----
  final TextEditingController listController = TextEditingController();
  bool isCheckingList = false;

  @override
  void initState() {
    super.initState();
    loadFilters();
  }

  @override
  void dispose() {
    listController.dispose();
    super.dispose();
  }

  void _snack(String message, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: error ? Colors.red : null),
    );
  }

  String? _q(String value) => value == _all ? null : value;

  String _msg(Object e) => e.toString().replaceFirst("Exception: ", "");

  Future<void> loadFilters() async {
    setState(() => isLoadingFilters = true);
    try {
      final data = await ApiService.fetchFilters();
      if (!mounted) return;
      setState(() {
        years = List<String>.from(data["years"]);
        departments = List<String>.from(data["departments"]);
        sections = List<String>.from(data["sections"]);
      });
    } catch (e) {
      if (!mounted) return;
      _snack("Failed to load filters: ${_msg(e)}", error: true);
    }
    if (mounted) setState(() => isLoadingFilters = false);
  }

  // ------------------------- option 1 -------------------------

  Future<void> check() async {
    setState(() {
      isChecking = true;
      result = null;
    });
    try {
      final data = await ApiService.getClassAvailability(
        year: _q(selectedYear),
        department: _q(selectedDepartment),
        section: _q(selectedSection),
      );
      if (!mounted) return;
      setState(() => result = data);
    } catch (e) {
      if (!mounted) return;
      _snack(_msg(e), error: true);
    }
    if (mounted) setState(() => isChecking = false);
  }

  Future<void> downloadAvailablePdf() async {
    setState(() => isDownloading = true);
    try {
      final response = await ApiService.downloadClassAvailabilityPdf(
        year: _q(selectedYear),
        department: _q(selectedDepartment),
        section: _q(selectedSection),
      );
      if (response.statusCode != 200) {
        throw Exception("Server returned ${response.statusCode}");
      }

      await FileSaver.instance.saveFile(
        name: "Available_Classes",
        bytes: Uint8List.fromList(response.bodyBytes),
        ext: "pdf",
        mimeType: MimeType.pdf,
      );

      if (!mounted) return;
      _snack("Available classes PDF downloaded");
    } catch (e) {
      if (!mounted) return;
      _snack("Failed to download PDF: ${_msg(e)}", error: true);
    }
    if (mounted) setState(() => isDownloading = false);
  }

  // ------------------------- option 2 -------------------------

  Future<void> checkClassList() async {
    final text = listController.text.trim();
    if (text.isEmpty) {
      _snack("Paste the class list first", error: true);
      return;
    }

    setState(() => isCheckingList = true);
    try {
      final response = await ApiService.checkClassListMissingPdf(text: text);

      await FileSaver.instance.saveFile(
        name: "Missing_Classes",
        bytes: Uint8List.fromList(response.bodyBytes),
        ext: "pdf",
        mimeType: MimeType.pdf,
      );

      if (!mounted) return;
      _snack("Missing classes PDF downloaded");
    } catch (e) {
      if (!mounted) return;
      _snack(_msg(e), error: true);
    }
    if (mounted) setState(() => isCheckingList = false);
  }

  // ------------------------- widgets -------------------------

  Widget _dropdown(String label, String value, List<String> options, void Function(String) onChanged) {
    return DropdownButtonFormField<String>(
      value: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
      items: [_all, ...options].map((o) => DropdownMenuItem(value: o, child: Text(o))).toList(),
      onChanged: (v) {
        if (v == null) return;
        setState(() {
          onChanged(v);
          result = null; // the old result no longer matches the selection
        });
      },
    );
  }

  Widget _resultCard() {
    final available = List<Map<String, dynamic>>.from(result!["available"] as List);
    final none = available.isEmpty;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  none ? Icons.error_outline : Icons.check_circle,
                  color: none ? Colors.red : Colors.green,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    none
                        ? "No classes in this selection were found in Google Classroom."
                        : "Available in Google Classroom",
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            if (!none) ...[
              const SizedBox(height: 12),
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 220),
                child: SingleChildScrollView(
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: available
                        .map((a) => Chip(
                              avatar: const Icon(Icons.check, size: 16, color: Colors.green),
                              label: Text("${a["year"]} · ${a["department"]} · ${a["section"]}"),
                            ))
                        .toList(),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _checkByFiltersCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text("Check by Year / Department / Section",
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text(
              "Leave a filter on \"All\" to include every value — for "
              "example, choose only a Year to check every department "
              "and section of that year. Downloads the classes that "
              "ARE in Google Classroom.",
              style: TextStyle(color: Colors.grey, fontSize: 12),
            ),
            const SizedBox(height: 16),

            if (isLoadingFilters)
              const Padding(
                padding: EdgeInsets.all(20),
                child: Center(child: CircularProgressIndicator()),
              )
            else
              Row(
                children: [
                  Expanded(child: _dropdown("Year", selectedYear, years, (v) => selectedYear = v)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _dropdown("Department", selectedDepartment, departments, (v) => selectedDepartment = v),
                  ),
                  const SizedBox(width: 10),
                  Expanded(child: _dropdown("Section", selectedSection, sections, (v) => selectedSection = v)),
                ],
              ),

            const SizedBox(height: 16),

            ElevatedButton.icon(
              onPressed: (isChecking || isLoadingFilters) ? null : check,
              icon: const Icon(Icons.fact_check),
              label: Text(isChecking ? "Checking Google Classroom..." : "Check Availability"),
            ),

            if (isChecking)
              const Padding(
                padding: EdgeInsets.only(top: 16),
                child: LinearProgressIndicator(),
              ),

            if (result != null) ...[
              const SizedBox(height: 16),
              _resultCard(),
              const SizedBox(height: 12),
              ElevatedButton.icon(
                onPressed: isDownloading ? null : downloadAvailablePdf,
                icon: const Icon(Icons.picture_as_pdf),
                label: Text(isDownloading ? "Preparing PDF..." : "Download Available Classes (PDF)"),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _pasteCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text("Match a class list",
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text(
              "In Excel, select the Year, Department and Section columns "
              "(with or without the header row), copy them, and paste "
              "below — one row per class that should exist. Years can be "
              "written I, III, 3 or III-Yr. The classes missing from "
              "Google Classroom are downloaded as a PDF.",
              style: TextStyle(color: Colors.grey, fontSize: 12),
            ),
            const SizedBox(height: 14),

            TextField(
              controller: listController,
              enabled: !isCheckingList,
              keyboardType: TextInputType.multiline,
              minLines: 6,
              maxLines: 12,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                alignLabelWithHint: true,
                labelText: "Class list",
                hintText: "Year   Department   Section\nIII   CSE   A\nIII   CSE   B\nII   IT   A",
              ),
            ),

            const SizedBox(height: 14),

            Row(
              children: [
                ElevatedButton.icon(
                  onPressed: isCheckingList ? null : checkClassList,
                  icon: const Icon(Icons.picture_as_pdf),
                  label: Text(isCheckingList
                      ? "Checking Google Classroom..."
                      : "Check & Download Missing Classes (PDF)"),
                ),
                const SizedBox(width: 10),
                TextButton(
                  onPressed: isCheckingList ? null : () => listController.clear(),
                  child: const Text("Clear"),
                ),
              ],
            ),

            if (isCheckingList)
              const Padding(
                padding: EdgeInsets.only(top: 16),
                child: LinearProgressIndicator(),
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Class Availability")),
      body: Center(
        child: SizedBox(
          width: 700,
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              _pasteCard(),
              const SizedBox(height: 16),
              _checkByFiltersCard(),
            ],
          ),
        ),
      ),
    );
  }
}
