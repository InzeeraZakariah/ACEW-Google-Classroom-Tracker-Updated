import 'package:flutter/material.dart';

class AcademicConfigScreen extends StatefulWidget {
  const AcademicConfigScreen({super.key});

  @override
  State<AcademicConfigScreen> createState() =>
      _AcademicConfigScreenState();
}

class _AcademicConfigScreenState
    extends State<AcademicConfigScreen> {

  String? selectedRegulation;

  final regulations = [
    "2021",
    "2025",
    "2029",
    "2033",
  ];

  void uploadExcel() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          "Excel picker will be connected to the backend API.",
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Academic Configuration"),
      ),

      body: Center(
        child: SizedBox(
          width: 750,
          child: ListView(
            padding: const EdgeInsets.all(30),
            children: [
              const Text(
                "Academic Configuration",
                style: TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                ),
              ),

              const SizedBox(height: 10),

              const Text(
                "Upload the academic configuration maintained by the Dean.",
              ),

              const SizedBox(height: 30),

              DropdownButtonFormField<String>(
                value: selectedRegulation,
                decoration: const InputDecoration(
                  labelText: "Regulation",
                  border: OutlineInputBorder(),
                ),
                items: regulations.map(
                  (regulation) {
                    return DropdownMenuItem(
                      value: regulation,
                      child: Text(regulation),
                    );
                  },
                ).toList(),
                onChanged: (value) {
                  setState(() {
                    selectedRegulation = value;
                  });
                },
              ),

              const SizedBox(height: 30),

              Container(
                padding: const EdgeInsets.all(25),
                decoration: BoxDecoration(
                  border: Border.all(),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Column(
                  children: [
                    Icon(
                      Icons.table_chart,
                      size: 50,
                    ),

                    SizedBox(height: 15),

                    Text(
                      "Excel Format",
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),

                    SizedBox(height: 10),

                    Text(
                      "Yr | Department | Semester | Section | "
                      "Regulation | Subject | Unit Count",
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 30),

              ElevatedButton.icon(
                onPressed: uploadExcel,
                icon: const Icon(Icons.upload_file),
                label: const Text(
                  "Upload Academic Excel",
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}