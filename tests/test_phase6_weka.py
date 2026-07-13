"""Phase 6 WEKA interoperability tests using tiny explicit fixtures."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import sparse

from src.data.weka_export import export_sparse_arff, ordered_checksum, product_alias, sparse_arff_row
from src.weka.arff_validation import parse_sparse_row, validate_sparse_arff
from src.weka.parameter_alignment import build_parameter_alignment, validate_parameter_alignment
from src.weka.python_weka_audit import aligned_python_rules, audit_python_weka_rules
from src.weka.runtime_comparison import summarize_runtime, validate_runtime_metadata
from src.weka.weka_metrics import METRIC_TOLERANCES, support_from_count, values_match
from src.weka.weka_rule_canonicalization import canonicalize_weka_rules
from src.weka.weka_rule_parser import RAW_RULE_COLUMNS, parse_weka_rule_export


@pytest.fixture()
def tiny_basket(tmp_path: Path) -> dict[str, object]:
    matrix = sparse.csr_matrix(np.array([[1, 0, 1], [0, 1, 1]], dtype=np.uint8))
    columns = pd.DataFrame(
        {"column_index": [0, 1, 2], "StockCode": ["A", "B", "C"],
         "Description": ["Alpha", "Beta", "Gamma"], "ProductLabel": ["A", "B", "C"]}
    )
    transactions = pd.DataFrame({"row_index": [0, 1], "InvoiceNo": ["T1", "T2"]})
    paths = {name: tmp_path / name for name in (
        "basket.arff", "products.csv", "transactions.csv", "metadata.json")}
    export_sparse_arff(
        matrix, columns, transactions, arff_path=paths["basket.arff"],
        product_mapping_path=paths["products.csv"],
        transaction_mapping_path=paths["transactions.csv"], metadata_path=paths["metadata.json"])
    return {"matrix": matrix, "columns": columns, "transactions": transactions, **paths}


@pytest.fixture()
def raw_rule_csv(tmp_path: Path) -> Path:
    row = {
        "rule_index": 0, "premise_aliases": '["P_000000"]',
        "consequence_aliases": '["P_000002"]', "premise_support_count": 2,
        "consequence_support_count": 2, "total_support_count": 2,
        "transaction_count": 4, "confidence": 1.0, "lift": 2.0,
        "leverage": 0.25, "conviction": np.inf, "primary_metric_name": "Confidence",
        "primary_metric_value": 1.0,
        "metric_names": '["Confidence","Lift","Leverage","Conviction"]',
        "metric_values": '[1.0,2.0,0.25,Infinity]', "weka_rule_text": "P_000000=1 ==> P_000002=1",
    }
    path = tmp_path / "rules.csv"
    pd.DataFrame([row], columns=sorted(RAW_RULE_COLUMNS)).to_csv(path, index=False)
    return path


def _mapping() -> pd.DataFrame:
    return pd.DataFrame(
        {"arff_attribute": ["P_000000", "P_000001", "P_000002"],
         "StockCode": ["A", "B", "C"], "Description": ["Alpha", "Beta", "Gamma"]}
    )


def _python_rule(key: str = "A => C") -> pd.DataFrame:
    return pd.DataFrame([{
        "rule_key": key, "support": 0.5, "support_count": 2, "confidence": 1.0,
        "lift": 2.0, "leverage": 0.25, "conviction": np.inf,
        "antecedent_length": 1, "consequent_length": 1,
    }])


def test_sparse_arff_row_generation() -> None:
    assert sparse_arff_row([0, 2, 8]) == "{0 1,2 1,8 1}"


def test_binary_nominal_encoding(tiny_basket: dict[str, object]) -> None:
    text = Path(tiny_basket["basket.arff"]).read_text(encoding="utf-8")
    assert text.count("{0,1}") == 3
    assert "% Binary nominal attributes: 0=absent" in text


def test_product_alias_uniqueness() -> None:
    aliases = [product_alias(index) for index in range(10000)]
    assert len(aliases) == len(set(aliases))


def test_product_mapping_round_trip(tiny_basket: dict[str, object]) -> None:
    mapping = pd.read_csv(tiny_basket["products.csv"], dtype=str)
    assert dict(zip(mapping.arff_attribute, mapping.StockCode))["P_000001"] == "B"


def test_transaction_order_preservation(tiny_basket: dict[str, object]) -> None:
    rows = pd.read_csv(tiny_basket["transactions.csv"], dtype=str)
    assert rows.InvoiceNo.tolist() == ["T1", "T2"]
    metadata = json.loads(Path(tiny_basket["metadata.json"]).read_text(encoding="utf-8"))
    assert metadata["transaction_order_checksum"] == ordered_checksum(["T1", "T2"])


def test_arff_instance_and_attribute_counts(tiny_basket: dict[str, object]) -> None:
    mapping = pd.read_csv(tiny_basket["products.csv"], dtype={"StockCode": "string"})
    transactions = pd.read_csv(tiny_basket["transactions.csv"], dtype={"InvoiceNo": "string"})
    metadata = json.loads(Path(tiny_basket["metadata.json"]).read_text(encoding="utf-8"))
    result, _ = validate_sparse_arff(
        Path(tiny_basket["basket.arff"]), tiny_basket["matrix"], mapping, transactions,
        metadata, sampled_rows=(0, 1), sampled_attributes=(0, 1, 2))
    assert (result.instance_count, result.attribute_count) == (2, 3)


def test_presence_count_equivalence(tiny_basket: dict[str, object]) -> None:
    lines = Path(tiny_basket["basket.arff"]).read_text(encoding="utf-8").split("@data\n", 1)[1].splitlines()
    assert sum(len(parse_sparse_row(line, 3)) for line in lines) == 4


def test_weka_rule_parsing(raw_rule_csv: Path) -> None:
    parsed = parse_weka_rule_export(raw_rule_csv)
    assert parsed.iloc[0].premise_alias_tuple == ("P_000000",)


def test_weka_alias_canonicalization(raw_rule_csv: Path) -> None:
    canonical = canonicalize_weka_rules(parse_weka_rule_export(raw_rule_csv), _mapping())
    assert canonical.iloc[0].rule_key == "A => C"
    assert canonical.iloc[0].mapping_valid


def test_canonical_rule_matching(raw_rule_csv: Path) -> None:
    canonical = canonicalize_weka_rules(parse_weka_rule_export(raw_rule_csv), _mapping())
    audit, _, summary = audit_python_weka_rules(_python_rule(), canonical)
    assert audit.iloc[0].presence_status == "common"
    assert summary["common_rules"] == 1


def test_support_count_conversion() -> None:
    assert support_from_count(90, 17901) == 90 / 17901
    with pytest.raises(ValueError):
        support_from_count(2, 1)


def test_numeric_tolerance_behavior() -> None:
    tolerance = METRIC_TOLERANCES["confidence"]
    assert values_match(0.7, 0.7 + 5e-13, tolerance)
    assert not values_match(0.7, 0.7 + 2e-12, tolerance)


def test_missing_metric_handling(raw_rule_csv: Path) -> None:
    canonical = canonicalize_weka_rules(parse_weka_rule_export(raw_rule_csv), _mapping())
    canonical.loc[0, "conviction"] = np.nan
    _, _, summary = audit_python_weka_rules(_python_rule(), canonical)
    assert summary["rules_with_missing_metrics"] == 1
    assert summary["metric_mismatches"] == 1


def test_duplicate_rule_handling(raw_rule_csv: Path) -> None:
    canonical = canonicalize_weka_rules(parse_weka_rule_export(raw_rule_csv), _mapping())
    duplicated = pd.concat([canonical, canonical], ignore_index=True)
    _, _, summary = audit_python_weka_rules(_python_rule(), duplicated)
    assert summary["weka_duplicate_rows"] == 2


def test_python_only_and_weka_only_classification(raw_rule_csv: Path) -> None:
    canonical = canonicalize_weka_rules(parse_weka_rule_export(raw_rule_csv), _mapping())
    audit, _, summary = audit_python_weka_rules(_python_rule("B => C"), canonical)
    assert set(audit.presence_status) == {"python_only", "weka_only"}
    assert summary["python_only_rules"] == summary["weka_only_rules"] == 1


def test_parameter_alignment_validation() -> None:
    table = build_parameter_alignment({
        "positive_index": 2, "maximum_items": 3, "metric_type": "Confidence",
        "minimum_metric": 0.7, "lower_minimum_support": 0.005,
        "upper_minimum_support": 1.0, "find_all_rules": True,
        "requested_number_of_rules": 1000000, "support_delta": 0.005,
    })
    assert (table.alignment_status == "aligned").sum() >= 8


def test_runtime_metadata_completeness() -> None:
    row = {column: 0 for column in (
        "startup_seconds", "loading_seconds", "mining_seconds", "export_seconds",
        "end_to_end_seconds", "approximate_memory_bytes")}
    row.update({"environment": "test", "implementation": "Python", "run_kind": "measured",
                "run_number": 1, "status": "success", "startup_included": False,
                "loading_included": True, "mining_included": True})
    runs = pd.DataFrame([row])
    validate_runtime_metadata(runs)
    assert summarize_runtime(runs).iloc[0].measured_runs == 1


def test_java_bridge_output_schema(raw_rule_csv: Path) -> None:
    assert RAW_RULE_COLUMNS.issubset(pd.read_csv(raw_rule_csv, nrows=0).columns)


def test_invalid_weka_output_fails(tmp_path: Path) -> None:
    path = tmp_path / "invalid.csv"
    pd.DataFrame({"rule_index": [0]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        parse_weka_rule_export(path)


def test_audit_summary_reconciliation(raw_rule_csv: Path) -> None:
    canonical = canonicalize_weka_rules(parse_weka_rule_export(raw_rule_csv), _mapping())
    _, _, summary = audit_python_weka_rules(_python_rule(), canonical)
    assert summary["common_rules"] + summary["python_only_rules"] == summary["python_rule_count"]
    assert summary["common_rules"] + summary["weka_only_rules"] == summary["weka_rule_count"]


def test_java_tiny_arff_integration(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    java = root / "tools/weka/distribution/jre/jre-25.0.2-full/bin/java.exe"
    jar = root / "tools/weka/distribution/weka.jar"
    classes = root / "weka/java/classes"
    if not (java.exists() and jar.exists() and (classes / "WekaArffProbe.class").exists()):
        pytest.skip("Project-local official WEKA bridge has not been compiled")
    arff = tmp_path / "tiny.arff"
    arff.write_text("@relation tiny\n@attribute A {0,1}\n@attribute B {0,1}\n@data\n{0 1}\n{1 1}\n", encoding="utf-8")
    completed = subprocess.run(
        [str(java), "-cp", f"{classes};{jar}", "WekaArffProbe", str(arff)],
        capture_output=True, text=True, check=True)
    assert "instances=2" in completed.stdout
    assert "stored_values=2" in completed.stdout


def test_aligned_python_filter_excludes_lift_as_a_condition() -> None:
    rules = _python_rule()
    rules.loc[0, "lift"] = 0.5
    assert len(aligned_python_rules(rules, minimum_support_count=2)) == 1


def test_invalid_parameter_alignment_fails() -> None:
    table = pd.DataFrame({"concept": ["minimum support"], "weka_value": [0.01]})
    with pytest.raises(ValueError, match="alignment failed"):
        validate_parameter_alignment(table)
