from pathlib import Path

from openpyxl import Workbook

from app.services.samm_workbook_parser import SammWorkbookParser

SOURCE = Path(__file__).parents[1] / "data" / "SAMM_spreadsheet.xlsx"


def test_real_samm_workbook_is_parsed_without_errors():
    preview = SammWorkbookParser().parse(SOURCE)
    assert preview.source_version == "2.2.0"
    assert preview.summary == {
        "business_functions": 5,
        "security_practices": 15,
        "practice_streams": 30,
        "maturity_levels": 3,
        "questions": 90,
        "answer_sets": 24,
        "quality_criteria": 295,
        "errors": 0,
        "warnings": 0,
    }
    assert preview.questions[0]["external_code"] == "D-SA-A-1-1"
    assert preview.questions[0]["criteria"] == [
        "You have an agreed upon checklist of security principles",
        "You store your checklist in an accessible location",
        "Relevant stakeholders understand security principles",
    ]


def test_parser_reports_missing_required_sheets(tmp_path):
    path = tmp_path / "invalid.xlsx"
    workbook = Workbook()
    workbook.active.title = "Other"
    workbook.save(path)
    preview = SammWorkbookParser().parse(path)
    assert preview.summary["errors"] == 2
    assert {item.sheet for item in preview.errors} == {"imp-questions", "imp-answers"}
