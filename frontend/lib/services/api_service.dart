import 'dart:convert';
import 'package:http/http.dart' as http;

import '../models/classroom_model.dart';

class ApiService {
  // Set at build time, e.g.:
  //   flutter build windows --dart-define=API_BASE_URL=https://your-domain.com
  //   flutter build apk --dart-define=API_BASE_URL=https://your-domain.com
  // Falls back to localhost for local development when not provided.
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://acew-classroom-backend.onrender.com',
  );

  // Fetch Filters
  static Future<Map<String, dynamic>> fetchFilters() async {
    final response = await http.get(
      Uri.parse("$baseUrl/filters"),
    );

    if (response.statusCode != 200) {
      throw Exception("Failed to load filters");
    }

    return jsonDecode(response.body);
  }

  // Get Departments
  static Future<List<String>> getDepartments() async {
    final data = await fetchFilters();
    return List<String>.from(data["departments"]);
  }

  // Get Years
  static Future<List<String>> getYears() async {
    final data = await fetchFilters();
    return List<String>.from(data["years"]);
  }

  // Get Sections
  static Future<List<String>> getSections() async {
    final data = await fetchFilters();
    return List<String>.from(data["sections"]);
  }

  // ============================================================
  // FILTER OPTIONS — add / remove departments, years, sections
  // ============================================================
  // kind: "departments" | "years" | "sections". Both return the
  // updated {departments, years, sections} lists.

  static Map<String, List<String>> _decodeFilters(String body) {
    final json = jsonDecode(body) as Map<String, dynamic>;
    return {
      for (final entry in json.entries)
        entry.key: List<String>.from(entry.value as List),
    };
  }

  static Future<Map<String, List<String>>> addFilterOption(
    String kind,
    String value,
  ) async {
    final response = await http.post(
      Uri.parse("$baseUrl/filters/$kind"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"value": value}),
    );

    if (response.statusCode != 200) {
      throw Exception(_errorDetail(response, "Failed to add $value"));
    }

    return _decodeFilters(response.body);
  }

  // The value is URL-encoded so names like AI&DS survive the path.
  static Future<Map<String, List<String>>> removeFilterOption(
    String kind,
    String value,
  ) async {
    final response = await http.delete(
      Uri.parse("$baseUrl/filters/$kind/${Uri.encodeComponent(value)}"),
    );

    if (response.statusCode != 200) {
      throw Exception(_errorDetail(response, "Failed to remove $value"));
    }

    return _decodeFilters(response.body);
  }

  // ============================================================
  // CLASS AVAILABILITY
  // ============================================================
  // Leave year / department / section null for "all".

  static Map<String, String>? _availabilityQuery({
    String? year,
    String? department,
    String? section,
  }) {
    final query = {
      if (year != null && year.isNotEmpty) "year": year,
      if (department != null && department.isNotEmpty)
        "department": department,
      if (section != null && section.isNotEmpty) "section": section,
    };
    return query.isEmpty ? null : query;
  }

  // {scope, summary: {expected, available, missing},
  //  available: [{department, year, section, course_names}],
  //  missing: [{department, year, section}]}
  static Future<Map<String, dynamic>> getClassAvailability({
    String? year,
    String? department,
    String? section,
  }) async {
    final uri = Uri.parse("$baseUrl/class-availability").replace(
      queryParameters: _availabilityQuery(
        year: year,
        department: department,
        section: section,
      ),
    );

    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception(
        _errorDetail(response, "Failed to check class availability"),
      );
    }

    return Map<String, dynamic>.from(jsonDecode(response.body));
  }

  // PDF of only the classes that ARE found in Google Classroom.
  static Future<http.Response> downloadClassAvailabilityPdf({
    String? year,
    String? department,
    String? section,
  }) async {
    final uri = Uri.parse("$baseUrl/class-availability/pdf").replace(
      queryParameters: _availabilityQuery(
        year: year,
        department: department,
        section: section,
      ),
    );

    return await http.get(uri);
  }

  // Sends a class list pasted into the app (Year, Department, Section —
  // e.g. columns copied from Excel) and returns a PDF of the listed
  // classes that are NOT in Google Classroom. Throws with the server's
  // message on failure (e.g. "Paste the class list first.").
  static Future<http.Response> checkClassListMissingPdf({
    required String text,
  }) async {
    final response = await http.post(
      Uri.parse("$baseUrl/class-availability/check-list"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"text": text}),
    );

    if (response.statusCode != 200) {
      throw Exception(_errorDetail(response, "Failed to check the class list"));
    }

    return response;
  }

  // Fetch Classroom Records
  static Future<List<ClassroomModel>> fetchClassroomData({
    String? department,
    String? year,
    String? section,
  }) async {
    final uri = Uri.parse("$baseUrl/classroom-data").replace(
      queryParameters: {
        if (department != null && department.isNotEmpty)
          "department": department,
        if (year != null && year.isNotEmpty) "year": year,
        if (section != null && section.isNotEmpty) "section": section,
      },
    );

    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception("Failed to fetch classroom data");
    }

    final jsonData = jsonDecode(response.body);

    return (jsonData["records"] as List)
        .map((e) => ClassroomModel.fromJson(e))
        .toList();
  }

  // Wrapper for Existing Home Screen
  static Future<Map<String, dynamic>> fetchStaffData({
    String? department,
    String? year,
    String? section,
  }) async {
    final uri = Uri.parse("$baseUrl/classroom-data").replace(
      queryParameters: {
        if (department != null && department.isNotEmpty)
          "department": department,
        if (year != null && year.isNotEmpty) "year": year,
        if (section != null && section.isNotEmpty) "section": section,
      },
    );

    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception("Failed to fetch classroom data");
    }

    final jsonData = jsonDecode(response.body);

    return {
      "summary": jsonData["summary"],
      "records": (jsonData["records"] as List)
          .map((e) => ClassroomModel.fromJson(e))
          .toList(),
    };
  }

  // Download Excel (Filtered)
  static Future<http.Response> downloadExcel({
    String? department,
    String? year,
    String? section,
  }) async {
    final uri = Uri.parse("$baseUrl/download-excel").replace(
      queryParameters: {
        if (department != null && department.isNotEmpty)
          "department": department,
        if (year != null && year.isNotEmpty) "year": year,
        if (section != null && section.isNotEmpty) "section": section,
      },
    );

    return await http.get(uri);
  }

  // Download All Excel
  static Future<http.Response> downloadAllExcel() async {
    return await http.get(
      Uri.parse("$baseUrl/download-all"),
    );
  }

  // ============================================================
  // REGULATION TEMPLATES
  // ============================================================
  // A regulation holds the QA Part/Type structure and its Year/
  // Department scope (empty list == all). Due dates are set via the
  // Academic Calendar (see below).

  // Get Regulations
  static Future<List<Map<String, dynamic>>> getRegulations() async {
    final response = await http.get(
      Uri.parse("$baseUrl/regulations"),
    );

    if (response.statusCode != 200) {
      throw Exception("Failed to load regulations");
    }

    return List<Map<String, dynamic>>.from(jsonDecode(response.body));
  }

  // Save Regulation (also used to edit — send every field, not just
  // what changed, since this fully replaces the existing record)
  static Future<void> saveRegulation({
    required String name,
    required List<Map<String, String>> qaParts,
    List<String> years = const [],
    List<String> departments = const [],
  }) async {
    final response = await http.post(
      Uri.parse("$baseUrl/regulations"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "name": name,
        "qa_parts": qaParts,
        "years": years,
        "departments": departments,
      }),
    );

    if (response.statusCode != 200) {
      throw Exception("Failed to save regulation");
    }
  }

  // Does NOT cascade — any SubjectRequirement or academic-schedule
  // entries referencing this regulation by name are left as-is.
  static Future<void> deleteRegulation(String name) async {
    final response = await http.delete(Uri.parse("$baseUrl/regulations/$name"));

    if (response.statusCode != 200) {
      throw Exception("Failed to delete regulation");
    }
  }

  // Download Due Date Report (Excel) — one .xlsx workbook for a single
  // status ("Pending" or "Completed"), one sheet per course.
  //
  // If [date] is given, only subjects scheduled for that due date are
  // included. Otherwise the regulation's whole Year/Department scope
  // is used. See downloadDueDateReports() in report_downloader.dart,
  // which downloads both statuses.
  static Future<http.Response> downloadDueDateReport({
    required String regulation,
    required String status,
    String? date,
    String format = "xlsx", // "xlsx" or "pdf"
  }) async {
    final uri = Uri.parse("$baseUrl/due-date-report").replace(
      queryParameters: {
        "regulation": regulation,
        "status": status,
        "format": format,
        if (date != null && date.isNotEmpty) "date": date,
      },
    );

    return await http.get(uri);
  }

  // ============================================================
  // SUBJECT UNIT COUNTS (+ manual overrides)
  // ============================================================
  // `pairs` is a list of {"year", "department"} maps — deliberately
  // NOT two separate lists, since that shape would cross-multiply
  // Years x Departments instead of using the specific pairs picked.

  static Future<List<Map<String, dynamic>>> getSubjectUnitCounts({
    required List<Map<String, String>> pairs,
  }) async {
    final uri = Uri.parse("$baseUrl/subject-unit-counts").replace(
      queryParameters: {"pairs": _encodePairs(pairs)},
    );

    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception("Failed to fetch subject unit counts");
    }

    return List<Map<String, dynamic>>.from(jsonDecode(response.body));
  }

  static Future<http.Response> downloadSubjectUnitCountsExcel({
    required List<Map<String, String>> pairs,
  }) async {
    final uri = Uri.parse("$baseUrl/subject-unit-counts/excel").replace(
      queryParameters: {"pairs": _encodePairs(pairs)},
    );

    return await http.get(uri);
  }

  // Uploads whose titles don't follow the standard naming format, for
  // the given Year+Department pairs, as "xlsx" or "pdf".
  static Future<http.Response> downloadNamingMismatches({
    required List<Map<String, String>> pairs,
    String format = "xlsx",
  }) async {
    final uri = Uri.parse("$baseUrl/naming-mismatches").replace(
      queryParameters: {"pairs": _encodePairs(pairs), "format": format},
    );

    return await http.get(uri);
  }

  // Uses FastAPI's {"detail": "..."} message when present.
  static String _errorDetail(http.Response response, String fallback) {
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body["detail"] is String) {
        return body["detail"] as String;
      }
    } catch (_) {}
    return fallback;
  }

  // "III:CSE,II:IT" — see _parse_pairs in the backend routes.
  static String _encodePairs(List<Map<String, String>> pairs) {
    return pairs.map((p) => "${p['year']}:${p['department']}").join(",");
  }

  // Manually correct a subject's unit count. Subject NAMES always
  // come from Google Classroom and are never editable — only this.
  static Future<void> setSubjectUnitOverride({
    required String year,
    required String department,
    required String subject,
    required int unitCount,
  }) async {
    final response = await http.post(
      Uri.parse("$baseUrl/subject-unit-counts/override"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "year": year,
        "department": department,
        "subject": subject,
        "unit_count": unitCount,
      }),
    );

    if (response.statusCode != 200) {
      throw Exception("Failed to save unit count override");
    }
  }

  static Future<void> clearSubjectUnitOverride({
    required String year,
    required String department,
    required String subject,
  }) async {
    final uri = Uri.parse("$baseUrl/subject-unit-counts/override").replace(
      queryParameters: {
        "year": year,
        "department": department,
        "subject": subject,
      },
    );

    final response = await http.delete(uri);

    if (response.statusCode != 200) {
      throw Exception("Failed to clear unit count override");
    }
  }

  // ============================================================
  // ACADEMIC SCHEDULE (due dates, set via calendar clicks)
  // ============================================================

  static Future<List<Map<String, dynamic>>> getAcademicSchedule({
    String? regulation,
  }) async {
    final uri = Uri.parse("$baseUrl/academic-schedule").replace(
      queryParameters: regulation != null ? {"regulation": regulation} : null,
    );

    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception("Failed to load academic schedule");
    }

    return List<Map<String, dynamic>>.from(jsonDecode(response.body));
  }

  static Future<Map<String, dynamic>?> getAcademicScheduleEntry(
    String date,
  ) async {
    final response = await http.get(Uri.parse("$baseUrl/academic-schedule/$date"));

    if (response.statusCode == 404) return null;

    if (response.statusCode != 200) {
      throw Exception("Failed to load schedule entry");
    }

    return Map<String, dynamic>.from(jsonDecode(response.body));
  }

  // Saving only stores the date, regulation, Year+Department pairs and
  // required units — nothing is loaded from Google Classroom. `pairs`
  // is a list of {"year","department"} maps, deliberately not two
  // separate lists (which would cross-multiply).
  static Future<void> saveAcademicSchedule({
    required String date,
    required String regulation,
    required List<Map<String, String>> pairs,
    List<int> notesRequiredUnits = const [],
    List<int> assignmentRequiredUnits = const [],
    List<int> qaRequiredUnits = const [],
  }) async {
    final response = await http.post(
      Uri.parse("$baseUrl/academic-schedule"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "date": date,
        "regulation": regulation,
        "pairs": pairs,
        "notes_required_units": notesRequiredUnits,
        "assignment_required_units": assignmentRequiredUnits,
        "qa_required_units": qaRequiredUnits,
      }),
    );

    if (response.statusCode != 200) {
      throw Exception(_errorDetail(response, "Failed to save academic schedule"));
    }
  }

  static Future<void> deleteAcademicSchedule(String date) async {
    final response = await http.delete(Uri.parse("$baseUrl/academic-schedule/$date"));

    if (response.statusCode != 200) {
      throw Exception("Failed to delete schedule entry");
    }
  }

  // ============================================================
  // SUBJECT REQUIREMENTS (read-only listing; writes happen via the
  // Academic Calendar's schedule flow above)
  // ============================================================

  static Future<List<Map<String, dynamic>>> getRequirementsList() async {
    final response = await http.get(Uri.parse("$baseUrl/subject-requirements"));

    if (response.statusCode != 200) {
      throw Exception("Failed to load subject requirements");
    }

    return List<Map<String, dynamic>>.from(jsonDecode(response.body));
  }

  // ============================================================
  // HOLIDAYS
  // ============================================================

  static Future<List<Map<String, dynamic>>> getHolidays() async {
    final response = await http.get(Uri.parse("$baseUrl/holidays"));

    if (response.statusCode != 200) {
      throw Exception("Failed to load holidays");
    }

    return List<Map<String, dynamic>>.from(jsonDecode(response.body));
  }

  static Future<void> addHoliday({
    required String date,
    required String name,
  }) async {
    final response = await http.post(
      Uri.parse("$baseUrl/holidays"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"date": date, "name": name}),
    );

    if (response.statusCode != 200) {
      throw Exception("Failed to save holiday");
    }
  }

  static Future<void> deleteHoliday(String date) async {
    final response = await http.delete(Uri.parse("$baseUrl/holidays/$date"));

    if (response.statusCode != 200) {
      throw Exception("Failed to delete holiday");
    }
  }

  // Adds India's fixed-date national/widely-observed holidays for the
  // given year. Movable, lunar-calendar holidays (Diwali, Holi, Eid,
  // etc.) shift every year and aren't included — add those manually.
  static Future<void> seedIndianHolidays(int year) async {
    final uri = Uri.parse("$baseUrl/holidays/seed-indian").replace(
      queryParameters: {"year": year.toString()},
    );

    final response = await http.post(uri);

    if (response.statusCode != 200) {
      throw Exception("Failed to add Indian holidays");
    }
  }

  // ============================================================
  // ACADEMIC COMMENCEMENT DATES
  // ============================================================

  static Future<List<Map<String, dynamic>>> getCommencementDates() async {
    final response = await http.get(Uri.parse("$baseUrl/commencement-dates"));

    if (response.statusCode != 200) {
      throw Exception("Failed to load commencement dates");
    }

    return List<Map<String, dynamic>>.from(jsonDecode(response.body));
  }

  static Future<void> addCommencementDate({
    required String date,
    required String label,
  }) async {
    final response = await http.post(
      Uri.parse("$baseUrl/commencement-dates"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"date": date, "label": label}),
    );

    if (response.statusCode != 200) {
      throw Exception("Failed to save commencement date");
    }
  }

  static Future<void> deleteCommencementDate(String date) async {
    final response = await http.delete(Uri.parse("$baseUrl/commencement-dates/$date"));

    if (response.statusCode != 200) {
      throw Exception("Failed to delete commencement date");
    }
  }
}
