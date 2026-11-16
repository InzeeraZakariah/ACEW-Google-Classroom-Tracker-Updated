import 'dart:typed_data';
import 'package:file_saver/file_saver.dart';
import 'api_service.dart';

/// Downloads the due-date report as FOUR files:
///   Pending.xlsx, Pending.pdf, Completed.xlsx, Completed.pdf
/// The Excel files have one sheet per course; the PDFs are portrait A4
/// with the same tables.
///
/// If [date] is given, only subjects scheduled for that due date are
/// included (and only their Year/Department is fetched server-side).
/// Otherwise every schedule under the regulation is used.
///
/// Requests run one after the other, not in parallel: the backend
/// caches the (slow) Google Classroom fetch for a minute, so the later
/// requests reuse what the first one loaded.
///
/// Throws if any request fails, so callers can show one error message.
/// Files saved before the failure are already on disk — each is
/// complete on its own.
Future<void> downloadDueDateReports(String regulation, {String? date}) async {
  for (final status in const ["Pending", "Completed"]) {
    for (final format in const ["xlsx", "pdf"]) {
      final response = await ApiService.downloadDueDateReport(
        regulation: regulation,
        status: status,
        date: date,
        format: format,
      );

      if (response.statusCode != 200) {
        throw Exception(
          "Server returned ${response.statusCode} for the $status ${format.toUpperCase()} report",
        );
      }

      await FileSaver.instance.saveFile(
        name: date == null
            ? "Due_Date_Report_${regulation}_$status"
            : "Due_Date_Report_${regulation}_${date}_$status",
        bytes: Uint8List.fromList(response.bodyBytes),
        ext: format,
        mimeType: format == "pdf" ? MimeType.pdf : MimeType.microsoftExcel,
      );
    }
  }
}

/// Downloads the naming-mismatch report for the given Year+Department
/// pairs as one file — [format] is "xlsx" or "pdf".
Future<void> downloadNamingMismatches(
  List<Map<String, String>> pairs, {
  required String format,
}) async {
  final response = await ApiService.downloadNamingMismatches(
    pairs: pairs,
    format: format,
  );

  if (response.statusCode != 200) {
    throw Exception("Server returned ${response.statusCode}");
  }

  await FileSaver.instance.saveFile(
    name: "Naming_Mismatches",
    bytes: Uint8List.fromList(response.bodyBytes),
    ext: format,
    mimeType: format == "pdf" ? MimeType.pdf : MimeType.microsoftExcel,
  );
}