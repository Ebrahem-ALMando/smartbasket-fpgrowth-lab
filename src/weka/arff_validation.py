"""Independent streaming validation for the generated sparse binary ARFF."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
from scipy import sparse

from src.data.weka_export import ordered_checksum, product_alias


@dataclass(frozen=True)
class ArffValidationResult:
    """Aggregate and deterministic-sample validation evidence."""

    passed: bool
    instance_count: int
    attribute_count: int
    presence_count: int
    malformed_rows: int
    empty_rows: int
    non_binary_values: int
    sampled_rows_checked: int
    sampled_rows_matched: int
    sampled_attributes_checked: int
    sampled_attributes_matched: int
    product_order_checksum_match: bool
    transaction_order_checksum_match: bool


def parse_sparse_row(line: str, attribute_count: int) -> tuple[int, ...]:
    """Parse one sparse row and reject non-binary or non-canonical content."""
    stripped = line.strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        raise ValueError("Malformed sparse ARFF row")
    body = stripped[1:-1].strip()
    if not body:
        return ()
    indices: list[int] = []
    for field in body.split(","):
        parts = field.strip().split()
        if len(parts) != 2 or parts[1] != "1":
            raise ValueError("Sparse ARFF presence entries must be '<index> 1'")
        index = int(parts[0])
        if not 0 <= index < attribute_count:
            raise ValueError("Sparse ARFF attribute index is out of range")
        indices.append(index)
    if indices != sorted(set(indices)):
        raise ValueError("Sparse ARFF indices are not unique and increasing")
    return tuple(indices)


def validate_sparse_arff(
    arff_path: Path,
    matrix: sparse.spmatrix,
    product_mapping: pd.DataFrame,
    transaction_mapping: pd.DataFrame,
    export_metadata: dict[str, object],
    *,
    sampled_rows: tuple[int, ...] = (0, 1, 17, 901, 8950, 17899, 17900),
    sampled_attributes: tuple[int, ...] = (0, 1, 37, 511, 1895, 3789, 3790),
) -> tuple[ArffValidationResult, pd.DataFrame]:
    """Validate full counts and exact deterministic row/attribute samples."""
    csr = matrix.tocsr(copy=False)
    header_aliases: list[str] = []
    rows: dict[int, tuple[int, ...]] = {}
    presence_count = malformed_rows = empty_rows = non_binary_values = 0
    in_data = False
    instance_count = 0
    with arff_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("%"):
                continue
            lower = line.lower()
            if not in_data and lower.startswith("@attribute"):
                parts = line.split(maxsplit=2)
                if len(parts) != 3 or parts[2].replace(" ", "") != "{0,1}":
                    non_binary_values += 1
                else:
                    header_aliases.append(parts[1])
                continue
            if lower == "@data":
                in_data = True
                continue
            if not in_data or lower.startswith("@relation"):
                continue
            try:
                indices = parse_sparse_row(line, csr.shape[1])
            except (TypeError, ValueError):
                malformed_rows += 1
                indices = ()
            if not indices:
                empty_rows += 1
            presence_count += len(indices)
            if instance_count in sampled_rows:
                rows[instance_count] = indices
            instance_count += 1

    details: list[dict[str, object]] = []
    row_matches = 0
    for row_index in sampled_rows:
        if not 0 <= row_index < csr.shape[0]:
            continue
        start, end = csr.indptr[row_index : row_index + 2]
        expected = tuple(int(value) for value in csr.indices[start:end])
        actual = rows.get(row_index)
        matched = actual == expected
        row_matches += int(matched)
        details.append(
            {
                "check_type": "deterministic_row",
                "index": row_index,
                "identifier": str(transaction_mapping.iloc[row_index]["InvoiceNo"]),
                "expected": len(expected),
                "actual": len(actual) if actual is not None else None,
                "passed": matched,
            }
        )
    attribute_matches = 0
    for column_index in sampled_attributes:
        if not 0 <= column_index < csr.shape[1]:
            continue
        expected_alias = product_alias(column_index)
        actual_alias = (
            header_aliases[column_index] if column_index < len(header_aliases) else None
        )
        mapped_alias = str(product_mapping.iloc[column_index]["arff_attribute"])
        matched = expected_alias == actual_alias == mapped_alias
        attribute_matches += int(matched)
        details.append(
            {
                "check_type": "deterministic_attribute",
                "index": column_index,
                "identifier": str(product_mapping.iloc[column_index]["StockCode"]),
                "expected": expected_alias,
                "actual": actual_alias,
                "passed": matched,
            }
        )

    product_checksum_match = (
        ordered_checksum(product_mapping["StockCode"])
        == export_metadata["product_order_checksum"]
    )
    transaction_checksum_match = (
        ordered_checksum(transaction_mapping["InvoiceNo"])
        == export_metadata["transaction_order_checksum"]
    )
    passed = all(
        (
            instance_count == csr.shape[0] == int(export_metadata["instance_count"]),
            len(header_aliases) == csr.shape[1] == int(export_metadata["attribute_count"]),
            presence_count == csr.nnz == int(export_metadata["presence_count"]),
            malformed_rows == 0,
            empty_rows == 0,
            non_binary_values == 0,
            row_matches == sum(0 <= row < csr.shape[0] for row in sampled_rows),
            attribute_matches
            == sum(0 <= col < csr.shape[1] for col in sampled_attributes),
            product_checksum_match,
            transaction_checksum_match,
        )
    )
    result = ArffValidationResult(
        passed=passed,
        instance_count=instance_count,
        attribute_count=len(header_aliases),
        presence_count=presence_count,
        malformed_rows=malformed_rows,
        empty_rows=empty_rows,
        non_binary_values=non_binary_values,
        sampled_rows_checked=sum(0 <= row < csr.shape[0] for row in sampled_rows),
        sampled_rows_matched=row_matches,
        sampled_attributes_checked=sum(
            0 <= col < csr.shape[1] for col in sampled_attributes
        ),
        sampled_attributes_matched=attribute_matches,
        product_order_checksum_match=product_checksum_match,
        transaction_order_checksum_match=transaction_checksum_match,
    )
    aggregate = [
        ("instance_count", csr.shape[0], instance_count),
        ("attribute_count", csr.shape[1], len(header_aliases)),
        ("presence_count", int(csr.nnz), presence_count),
        ("malformed_rows", 0, malformed_rows),
        ("empty_rows", 0, empty_rows),
        ("non_binary_values", 0, non_binary_values),
    ]
    for name, expected, actual in aggregate:
        details.append(
            {
                "check_type": "aggregate",
                "index": None,
                "identifier": name,
                "expected": expected,
                "actual": actual,
                "passed": expected == actual,
            }
        )
    return result, pd.DataFrame(details)


def save_validation_outputs(
    result: ArffValidationResult,
    details: pd.DataFrame,
    *,
    detailed_csv: Path,
    summary_json: Path,
    compact_csv: Path,
) -> None:
    """Persist traceable detailed and compact input-equivalence evidence."""
    for path in (detailed_csv, summary_json, compact_csv):
        path.parent.mkdir(parents=True, exist_ok=True)
    details.to_csv(detailed_csv, index=False, encoding="utf-8", lineterminator="\n")
    document = asdict(result)
    document["validation_scope"] = (
        "complete header/row/presence scan plus deterministic row and attribute samples"
    )
    summary_json.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    pd.DataFrame([document]).to_csv(
        compact_csv, index=False, encoding="utf-8", lineterminator="\n"
    )

