import 'package:flutter/material.dart';
import 'regulation_screen.dart';
import 'academic_calendar_screen.dart';
import 'subject_list_screen.dart';

// If your app already has a settings screen somewhere, add these
// three ListTiles into it instead of using this file directly — this
// is a standalone hub in case you don't have one yet.
class DeanSettingsScreen extends StatelessWidget {
  const DeanSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Due Date Settings")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _tile(
            context,
            icon: Icons.rule_folder,
            title: "Regulation Setup",
            subtitle: "QA structure and which Years/Departments each regulation applies to",
            builder: (_) => const RegulationSetupScreen(),
          ),
          const SizedBox(height: 12),
          _tile(
            context,
            icon: Icons.calendar_month,
            title: "Academic Calendar",
            subtitle: "Holidays, commencement dates, and due-date scheduling",
            builder: (_) => const AcademicCalendarScreen(),
          ),
          const SizedBox(height: 12),
          _tile(
            context,
            icon: Icons.list_alt,
            title: "Subjects List",
            subtitle: "Review and correct each subject's unit count",
            builder: (_) => const SubjectsListScreen(),
          ),
        ],
      ),
    );
  }

  Widget _tile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required WidgetBuilder builder,
  }) {
    return Card(
      child: ListTile(
        leading: Icon(icon, color: Colors.indigo),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: () {
          Navigator.push(context, MaterialPageRoute(builder: builder));
        },
      ),
    );
  }
}