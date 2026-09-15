"""Backward-compatible report helper retained for existing imports."""
from backend.app.utils.reporting import ReportGenerator


class PDFReportGenerator:
    @staticmethod
    def generate_reading_pdf(session_id, reading_data):
        return ReportGenerator.generate_pdf_report({"id": session_id, **reading_data}).getvalue()

    @staticmethod
    def generate_excel_report(session_id, reading_data):
        return ReportGenerator.generate_excel_report({"id": session_id, **reading_data}).getvalue()
