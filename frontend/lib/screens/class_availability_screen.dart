import 'dart:typed_data';
import 'package:file_saver/file_saver.dart';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

const String _all = "All";

// Checks whether classes exist in Google Classroom for the chosen
// Year / Department / Section ("All" = every value of that filter) and
// downloads the classes that are NOT there as a PDF.
class ClassAvailabilityScreen extends StatefulWidget {
  const ClassAvailabilityScreen({super.key});

  @override
  State<ClassAvailabilityScreen> createState() => _ClassAvailabilityScreenState();
}

class _ClassAvailabilityScreenState extends State<ClassAvailabilityScreen> {
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

  @override
  void initState() {
    super.initState();
    loadFilters();
  }

  void _snack(String message, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: error ? Colors.red : null),
    );
  }

  String? _q(String value) => value == _all ? null : value;

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
      _snack("Failed to load filters: $e", error: true);
    }
    if (mounted) setState(() => isLoadingFilters = false);
  }

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
      _snack("$e", error: true);
    }
    if (mounted) setState(() => isChecking = false);
  }

  Future<void> downloadPdf() async {
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
        name: "Unavailable_Classes",
        bytes: Uint8List.fromList(response.bodyBytes),
        ext: "pdf",
        mimeType: MimeType.pdf,
      );

      if (!mounted) return;
      _snack("Unavailable classes PDF downloaded");
    } catch (e) {
      if (!mounted) return;
      _snack("Failed to download PDF: $e", error: true);
    }
    if (mounted) setState(() => isDownloading = false);
  }

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
    final summary = result!["summary"] as Map<String, dynamic>;
    final missing = List<Map<String, dynamic>>.from(result!["missing"] as List);
    final expected = summary["expected"] as int;
    final available = summary["available"] as int;
    final allPresent = missing.isEmpty;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  allPresent ? Icons.check_circle : Icons.error_outline,
                  color: allPresent ? Colors.green : Colors.red,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    allPresent
                        ? (expected == 1
                            ? "This class is available in Google Classroom."
                            : "All $expected classes are available in Google Classroom.")
                        : "$available of $expected available — ${missing.length} not found",
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            if (!allPresent) ...[
              const SizedBox(height: 12),
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 220),
                child: SingleChildScrollView(
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: missing
                        .map((m) => Chip(
                              avatar: const Icon(Icons.close, size: 16, color: Colors.red),
                              label: Text("${m["year"]} · ${m["department"]} · ${m["section"]}"),
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Class Availability")),
      body: Center(
        child: SizedBox(
          width: 650,
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              const Text(
                "Check whether classes exist in Google Classroom. Leave a "
                "filter on \"All\" to check every value — for example, "
                "choose only a Year to check every department and section "
                "of that year.",
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 20),

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
                const SizedBox(height: 20),
                _resultCard(),
                const SizedBox(height: 16),
                ElevatedButton.icon(
                  onPressed: isDownloading ? null : downloadPdf,
                  icon: const Icon(Icons.picture_as_pdf),
                  label: Text(isDownloading ? "Preparing PDF..." : "Download Unavailable Classes (PDF)"),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}