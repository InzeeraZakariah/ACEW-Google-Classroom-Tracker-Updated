import 'dart:typed_data';
import 'package:file_saver/file_saver.dart';
import 'package:flutter/material.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import '../models/classroom_model.dart';
import '../services/api_service.dart';
import 'package:data_table_2/data_table_2.dart';
import '../widgets/dashboard_card.dart';
import 'dean_settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class BlinkingCredits extends StatefulWidget {
  const BlinkingCredits({super.key});

  @override
  State<BlinkingCredits> createState() => _BlinkingCreditsState();
}

// Blinking names in AppBar
class _BlinkingCreditsState extends State<BlinkingCredits>
    with SingleTickerProviderStateMixin {
  static const _credits = [
    ("Developed By", "Inzeera Z"),
    ("Supported By", "Dr. Dev R Newlin"),
  ];

  late final AnimationController _controller;
  int _index = 0;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );

    // fade in -> fade out -> switch to the next credit -> repeat
    _controller.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        Future.delayed(const Duration(milliseconds: 1200), () {
          if (mounted) _controller.reverse();
        });
      } else if (status == AnimationStatus.dismissed) {
        setState(() => _index = (_index + 1) % _credits.length);
        _controller.forward();
      }
    });

    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final (label, name) = _credits[_index];
    final style = Theme.of(context).textTheme.labelSmall;

    return FadeTransition(
      opacity: _controller,
      child: Text.rich(
        TextSpan(
          children: [
            TextSpan(text: "$label  "),
            TextSpan(
              text: name,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ],
        ),
        style: style,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}

class _HomeScreenState extends State<HomeScreen> {
  List<ClassroomModel> records = [];

  bool isLoading = false;

  int totalClasses = 0;
  int totalStaff = 0;
  int completedStaff = 0;
  int pendingStaff = 0;

  String? selectedDepartment;
  String? selectedYear;
  String? selectedSection;

  List<String> departments = [];
  List<String> years = ["I", "II", "III", "IV"];
  List<String> sections = ["A", "B", "C", "D"];

  @override
  void initState() {
    super.initState();

    loadDepartments();
  }

  // Load Departments
  Future<void> loadDepartments() async {
    departments = await ApiService.getDepartments();

    setState(() {});
  }

  // Fetch Google Classroom Data
  Future<void> fetchData({
    String? department,
    String? year,
    String? section,
  }) async {
    setState(() {
      isLoading = true;
    });

    try {
      final data = await ApiService.fetchClassroomData(
        department: department,
        year: year,
        section: section,
      );

      setState(() {
        records = data;
        totalClasses = data.map((e) => e.className).toSet().length;
        totalStaff = data.length;
        completedStaff = data
            .where((e) => e.pending.status == "Completed")
            .length;

        pendingStaff = totalStaff - completedStaff;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
    }
    setState(() {
      isLoading = false;
    });
  }

  // Download Excel Report
  Future<void> downloadExcel() async {
    try {
      final response = await ApiService.downloadExcel(
        department: selectedDepartment,
        year: selectedYear,
        section: selectedSection,
      );

      await FileSaver.instance.saveFile(
        name: "Google_Classroom_Report",
        bytes: Uint8List.fromList(response.bodyBytes),
        ext: "xlsx",
        mimeType: MimeType.microsoftExcel,
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Excel downloaded for one class successfully."),
        ),
      );
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
    }
  }

  // Download All Classes Excel
  Future<void> downloadAllExcel() async {
    try {
      final response = await ApiService.downloadAllExcel();

      if (response.statusCode != 200) {
        throw Exception("Server returned ${response.statusCode}");
      }

      // Saved with FileSaver like the single-class download — works on
      // web and on the Windows desktop app (dart:html does not).
      await FileSaver.instance.saveFile(
        name: "Google_Classroom_All_Classes",
        bytes: Uint8List.fromList(response.bodyBytes),
        ext: "xlsx",
        mimeType: MimeType.microsoftExcel,
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Excel downloaded for all classes successfully."),
        ),
      );
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
    }
  }

  // UI
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 64,
        leading: IconButton(
        icon: const Icon(Icons.info_outline),
        tooltip: "About",
        onPressed: showAboutDialogBox,
        ),

      title: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            "ACEW Classroom Tracker",
            style: TextStyle(fontWeight: FontWeight.bold),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          SizedBox(width: 12),
          Flexible(child: BlinkingCredits()),
        ],
      ),

      actions: [
        // Settings
        IconButton(
          tooltip: "Settings",
          icon: const Icon(Icons.admin_panel_settings_outlined),
          onPressed: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const DeanSettingsScreen(),
              ),
            );
          },
        ),

        Padding(
            padding: const EdgeInsets.only(right: 15),
            child: Center(
              child: Text(
                "Records : ${records.length}",
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
      ),

      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // Filters + Buttons
            Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        value: selectedDepartment,
                        decoration: const InputDecoration(
                          labelText: "Department",
                          border: OutlineInputBorder(),
                        ),
                        items: departments
                            .map(
                              (e) => DropdownMenuItem(value: e, child: Text(e)),
                            )
                            .toList(),
                        onChanged: (value) {
                          setState(() {
                            selectedDepartment = value;
                          });
                        },
                      ),
                    ),

                    const SizedBox(width: 10),

                    Expanded(
                      child: DropdownButtonFormField<String>(
                        value: selectedYear,
                        decoration: const InputDecoration(
                          labelText: "Year",
                          border: OutlineInputBorder(),
                        ),
                        items: years
                            .map(
                              (e) => DropdownMenuItem(value: e, child: Text(e)),
                            )
                            .toList(),
                        onChanged: (value) {
                          setState(() {
                            selectedYear = value;
                          });
                        },
                      ),
                    ),

                    const SizedBox(width: 10),

                    Expanded(
                      child: DropdownButtonFormField<String>(
                        value: selectedSection,
                        decoration: const InputDecoration(
                          labelText: "Section",
                          border: OutlineInputBorder(),
                        ),
                        items: sections
                            .map(
                              (e) => DropdownMenuItem(value: e, child: Text(e)),
                            )
                            .toList(),
                        onChanged: (value) {
                          setState(() {
                            selectedSection = value;
                          });
                        },
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 15),

                Row(
                  children: [
                    ElevatedButton.icon(
                      onPressed: () {
                        fetchData(
                          department: selectedDepartment,
                          year: selectedYear,
                          section: selectedSection,
                        );
                      },
                      icon: const Icon(Icons.search),
                      label: const Text("View Records"),
                    ),

                    const SizedBox(width: 15),

                    ElevatedButton.icon(
                      onPressed: records.isEmpty ? null : downloadExcel,
                      icon: const Icon(Icons.table_view),
                      label: const Text("Download Excel for One class"),
                    ),

                    const SizedBox(width: 15),

                    ElevatedButton.icon(
                      onPressed: downloadAllExcel,
                      icon: const Icon(Icons.download),
                      label: const Text("Download All Classes"),
                    ),
                  ],
                ),
              ],
            ),

            const SizedBox(height: 25),
            // Loading
            if (isLoading)
              const Expanded(
                child: Center(
                  child: SpinKitFadingCircle(color: Colors.indigo, size: 60),
                ),
              )
            else
              Expanded(
                child: Column(
                  children: [
                    // Dashboard Cards
                    Row(
                      children: [
                        const SizedBox(width: 10),

                        DashboardCard(
                          title: "Classes",
                          value: totalClasses.toString(),
                          icon: Icons.class_,
                          color: Colors.blue,
                        ),

                        DashboardCard(
                          title: "Staff",
                          value: totalStaff.toString(),
                          icon: Icons.people,
                          color: Colors.green,
                        ),

                        DashboardCard(
                          title: "Completed",
                          value: completedStaff.toString(),
                          icon: Icons.check_circle,
                          color: Colors.teal,
                        ),

                        DashboardCard(
                          title: "Pending",
                          value: pendingStaff.toString(),
                          icon: Icons.pending_actions,
                          color: Colors.red,
                        ),
                      ],
                    ),

                    const SizedBox(height: 20),
                    // Table
                    Expanded(
                      child: records.isEmpty
                          ? const Center(
                              child: Text(
                                "Click 'View Records' to load records.",

                                style: TextStyle(fontSize: 18),
                              ),
                            )
                          : buildTable(),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  // Staff Table
  // Name cells wrap onto up to 3 lines, and show the full text on
  // hover / long-press if it is still too long to fit.
  DataCell _nameCell(String text) {
    return DataCell(
      Tooltip(
        message: text,
        child: Text(text, maxLines: 3, overflow: TextOverflow.ellipsis),
      ),
    );
  }

  Widget buildTable() {
    return DataTable2(
      columnSpacing: 16,
      horizontalMargin: 16,
      minWidth: 1500,
      // Taller rows (the default is 48) so long class / staff /
      // subject names wrap onto a few lines instead of being cut off.
      dataRowHeight: 80,
      headingRowHeight: 56,
      headingRowColor: WidgetStateProperty.all(Colors.indigo.shade100),

      // Name columns get the extra width; the button columns stay
      // narrow.
      columns: const [
        DataColumn2(label: Text("Class"), size: ColumnSize.L),
        DataColumn2(label: Text("Staff"), size: ColumnSize.M),
        DataColumn2(label: Text("Subject"), size: ColumnSize.L),
        DataColumn2(label: Text("Notes"), size: ColumnSize.S),
        DataColumn2(label: Text("Assignments"), size: ColumnSize.S),
        DataColumn2(label: Text("Q&A"), size: ColumnSize.S),
        DataColumn2(label: Text("Duplicates"), size: ColumnSize.S),
      ],

      rows: records.map((record) {
        return DataRow(
          cells: [
            _nameCell(record.className),
            _nameCell(record.staffName),
            _nameCell(record.subject),
            // Notes
            DataCell(
              ElevatedButton(
                onPressed: () {
                  showNotesDialog(record);
                },

                child: Text("View (${record.notes.length})"),
              ),
            ),

            // Assignments
            DataCell(
              ElevatedButton(
                onPressed: () {
                  showAssignmentDialog(record);
                },
                child: Text("View (${record.assignments.length})"),
              ),
            ),
            // QA
            DataCell(
              ElevatedButton(
                onPressed: () {
                  showQADialog(record);
                },
                child: Text("View (${record.qa.length})"),
              ),
            ),
            // Duplicate Uploads
            DataCell(
              ElevatedButton(
                onPressed: () {
                  showDuplicateDialog(record);
                },
                child: const Text("View"),
              ),
            ),
            // Pending
           
            // Status
    
          ],
        );
      }).toList(),
    );
  }

  // Notes Dialog
  void showNotesDialog(ClassroomModel record) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Notes Uploaded"),
        content: SizedBox(
          width: 500,
          child: record.notes.isEmpty
              ? const Text("No Notes Uploaded")
              : ListView.builder(
                  shrinkWrap: true,
                  itemCount: record.notes.length,
                  itemBuilder: (_, index) {
                    final item = record.notes[index];
                    return ListTile(
                      leading: const Icon(Icons.menu_book),
                      title: Text(item.title),
                      subtitle: Text(item.date),
                    );
                  },
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Close"),
          ),
        ],
      ),
    );
  }

  // Assignment Dialog
  void showAssignmentDialog(ClassroomModel record) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Assignments"),
        content: SizedBox(
          width: 500,
          child: record.assignments.isEmpty
              ? const Text("No Assignments Uploaded")
              : ListView.builder(
                  shrinkWrap: true,
                  itemCount: record.assignments.length,
                  itemBuilder: (_, index) {
                    final item = record.assignments[index];
                    return ListTile(
                      leading: const Icon(Icons.assignment),

                      title: Text(item.title),

                      subtitle: Text(item.date),
                    );
                  },
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Close"),
          ),
        ],
      ),
    );
  }

  // QA Dialog
  void showQADialog(ClassroomModel record) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Question & Answer"),
        content: SizedBox(
          width: 550,
          child: record.qa.isEmpty
              ? const Text("No QA Uploaded")
              : ListView.builder(
                  shrinkWrap: true,
                  itemCount: record.qa.length,
                  itemBuilder: (_, index) {
                    final item = record.qa[index];

                    // Show the exact title as it appears in Google
                    // Classroom. Fall back to the parsed Unit/Part/Type
                    // composite only if the raw title is ever missing.
                    final label = item.title.isNotEmpty
                        ? item.title
                        : [
                            item.unit,
                            item.part,
                            item.qaType,
                          ].where((piece) => piece.isNotEmpty).join(" ");

                    return ListTile(
                      leading: const Icon(Icons.quiz),
                      title: Text(label),
                      subtitle: Text(item.date),
                    );
                  },
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Close"),
          ),
        ],
      ),
    );
  }

  // Duplicate Dialog
  void showDuplicateDialog(ClassroomModel record) {
    final duplicates = <String>[];
    for (final item in record.duplicates.notes) {
      duplicates.add("${item.label} (${item.count} times)");
    }
    for (final item in record.duplicates.assignments) {
      duplicates.add("${item.label} (${item.count} times)");
    }
    for (final item in record.duplicates.qa) {
      duplicates.add("${item.label} (${item.count} times)");
    }

    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Duplicate Uploads"),
        content: SizedBox(
          width: 500,
          child: duplicates.isEmpty
              ? const Text("No Duplicate Uploads")
              : ListView.builder(
                  shrinkWrap: true,
                  itemCount: duplicates.length,
                  itemBuilder: (_, index) {
                    return ListTile(
                      leading: const Icon(Icons.copy, color: Colors.orange),
                      title: Text(duplicates[index]),
                    );
                  },
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Close"),
          ),
        ],
      ),
    );
  }

  
  // About Dialog
  void showAboutDialogBox() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Row(
            children: const [
              Icon(Icons.info_outline, color: Colors.indigo),
              SizedBox(width: 10),
              Text("About"),
            ],
          ),

          content: SizedBox(
            width: 650,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Center(
                    child: Text(
                      "ACEW Google Classroom Tracker",
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),

                  SizedBox(height: 5),

                  Center(
                    child: Text(
                      "Version 1.0",
                      style: TextStyle(
                        color: Colors.grey,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),

                  Divider(height: 30),

                  Text(
                    "ACEW Google Classroom Tracker is an academic monitoring platform developed to help administrators, Heads of Departments, and faculty efficiently monitor Google Classroom activities across all courses and batches. The system automatically collects classroom data and presents it through an organized dashboard, enabling better curriculum tracking and academic transparency.",
                    textAlign: TextAlign.justify,
                  ),

                  SizedBox(height: 20),

                  Text(
                    "Key Features",
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 18,
                      color: Colors.indigo,
                    ),
                  ),

                  SizedBox(height: 10),

                  Text(
                    "• Track Notes, Assignments, and Question & Answer materials",
                  ),
                  Text("• Monitor unit-wise academic progress"),
                  Text("• Identify pending coursework and incomplete uploads"),
                  Text("• Generate structured reports for departments"),
                  Text("• Real-time integration with Google Classroom"),
                  Text("• Centralized dashboard for academic monitoring"),

                  SizedBox(height: 25),

                  Text(
                    "Leadership & Administrative Support",
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 18,
                      color: Colors.indigo,
                    ),
                  ),

                  SizedBox(height: 10),

                  Text(
                    "This platform was developed with the support and encouragement of the institution's leadership.",
                  ),

                  SizedBox(height: 10),

                  Text("Chairman : Dr. T. Krishnaswamy"),
                  Text("Principal : Dr. S. Joseph Jawhar"),
                  Text("Director : Er. K. S. Dharun Surath"),

                  Text("Dean : Dr. Dev R. Newlin"),

                  SizedBox(height: 25),

                  Text(
                    "Development",
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 18,
                      color: Colors.indigo,
                    ),
                  ),

                  SizedBox(height: 10),

                  Text(
                    "Developed By",
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),

                  Text("Ms. Inzeera Z"),

                  SizedBox(height: 10),

                  Text(
                    "Department",
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),

                  Text("B.Tech (Hons.) Artificial Intelligence & Data Science"),

                  SizedBox(height: 10),

                  Text("Batch", style: TextStyle(fontWeight: FontWeight.bold)),

                  Text("2023–2027"),

                  Divider(height: 30),

                  Center(
                    child: Text(
                      "Arunachala College of Engineering for Women (ACEW)",
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 17,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),

                  SizedBox(height: 8),

                  Center(
                    child: Text(
                      "Empowering academic excellence through digital innovation.",
                      style: TextStyle(
                        fontStyle: FontStyle.italic,
                        color: Colors.grey,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ),
            ),
          ),

          actions: [
            ElevatedButton.icon(
              onPressed: () => Navigator.pop(context),
              icon: const Icon(Icons.close),
              label: const Text("Close"),
            ),
          ],
        );
      },
    );
  }
}
