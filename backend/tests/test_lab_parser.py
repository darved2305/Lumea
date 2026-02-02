"""
LabParser unit tests (backend/src/services/lab_parser.py).
"""

from src.services.lab_parser import LabParser


def test_parse_reference_range_variants():
    p = LabParser()
    assert p.parse_reference_range("13.0-17.0") == (13.0, 17.0)
    assert p.parse_reference_range("< 5.0") == (None, 5.0)
    assert p.parse_reference_range("> 100") == (100.0, None)


def test_parse_line_extracts_metric_value_unit_and_ranges():
    p = LabParser()
    metric = p.parse_line("HEMOGLOBIN (HB) 12.8 g/dl 13.0-17.0 Low", page_num=2)
    assert metric is not None
    assert metric.test_name.lower().startswith("hemoglobin")
    assert metric.canonical_key == "hemoglobin"
    assert metric.value == 12.8
    assert metric.unit == "g/dL"
    assert metric.ref_range_low == 13.0
    assert metric.ref_range_high == 17.0
    assert metric.flag.lower() == "low"
    assert metric.page_num == 2


def test_parse_skips_headers_and_blank_lines():
    p = LabParser()
    assert p.parse_line("") is None
    assert p.parse_line("TEST NAME RESULT UNIT") is None


def test_parse_tracks_page_numbers():
    p = LabParser()
    text = "\n".join(
        [
            "=== PAGE 1 ===",
            "GLUCOSE 95 mg/dL 70-100",
            "=== PAGE 2 ===",
            "LDL CHOLESTEROL 160 mg/dL 0-130 High",
        ]
    )
    metrics = p.parse(text)
    assert len(metrics) == 2
    assert metrics[0].page_num == 1
    assert metrics[1].page_num == 2
