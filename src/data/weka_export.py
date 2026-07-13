"""Streaming export of the frozen binary basket to sparse WEKA ARFF."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from scipy import sparse


@dataclass(frozen=True)
class ArffExportResult:
    """Metadata for one completed sparse ARFF export."""

    arff_path: Path
    instance_count: int
    attribute_count: int
    presence_count: int
    byte_size: int
    sha256: str
    product_order_checksum: str
    transaction_order_checksum: str


def product_alias(column_index: int) -> str:
    """Return a collision-free deterministic ARFF-safe product alias."""
    if column_index < 0:
        raise ValueError("column_index must be non-negative")
    return f"P_{column_index:06d}"


def ordered_checksum(values: Iterable[object]) -> str:
    """Hash an ordered sequence with an unambiguous UTF-8 record separator."""
    digest = hashlib.sha256()
    for value in values:
        encoded = str(value).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def sparse_arff_row(indices: Iterable[int]) -> str:
    """Serialize present column indices; omitted nominal values default to absence."""
    ordered = [int(index) for index in indices]
    if ordered != sorted(set(ordered)):
        raise ValueError("Sparse ARFF indices must be unique and increasing")
    return "{" + ",".join(f"{index} 1" for index in ordered) + "}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def export_sparse_arff(
    matrix: sparse.spmatrix,
    column_metadata: pd.DataFrame,
    transaction_index: pd.DataFrame,
    *,
    arff_path: Path,
    product_mapping_path: Path,
    transaction_mapping_path: Path,
    metadata_path: Path,
    relation_name: str = "online_retail_uk_binary",
) -> ArffExportResult:
    """Export the exact CSR row/column order without constructing dense data."""
    csr = matrix.tocsr(copy=False)
    csr.sort_indices()
    if csr.shape != (len(transaction_index), len(column_metadata)):
        raise ValueError("Matrix shape does not match transaction/product mappings")
    if csr.nnz and not (csr.data == 1).all():
        raise ValueError("WEKA export requires a binary presence matrix")
    expected_columns = list(range(csr.shape[1]))
    actual_columns = column_metadata["column_index"].astype(int).tolist()
    if actual_columns != expected_columns:
        raise ValueError("Product metadata is not in exact zero-based column order")
    expected_rows = list(range(csr.shape[0]))
    actual_rows = transaction_index["row_index"].astype(int).tolist()
    if actual_rows != expected_rows:
        raise ValueError("Transaction metadata is not in exact zero-based row order")
    if (csr.getnnz(axis=1) == 0).any():
        raise ValueError("Empty basket rows are not permitted")

    arff_path.parent.mkdir(parents=True, exist_ok=True)
    product_mapping_path.parent.mkdir(parents=True, exist_ok=True)
    transaction_mapping_path.parent.mkdir(parents=True, exist_ok=True)

    mapping = column_metadata.copy()
    mapping.insert(1, "arff_attribute", [product_alias(i) for i in expected_columns])
    if not mapping["arff_attribute"].is_unique:
        raise AssertionError("Generated product aliases are not unique")
    mapping.to_csv(product_mapping_path, index=False, encoding="utf-8", lineterminator="\n")
    transaction_index.to_csv(
        transaction_mapping_path, index=False, encoding="utf-8", lineterminator="\n"
    )

    with arff_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"@relation {relation_name}\n\n")
        handle.write("% Binary nominal attributes: 0=absent (sparse default), 1=present\n")
        for alias in mapping["arff_attribute"]:
            handle.write(f"@attribute {alias} {{0,1}}\n")
        handle.write("\n@data\n")
        for row_index in range(csr.shape[0]):
            start, end = csr.indptr[row_index : row_index + 2]
            handle.write(sparse_arff_row(csr.indices[start:end]))
            handle.write("\n")

    result = ArffExportResult(
        arff_path=arff_path,
        instance_count=csr.shape[0],
        attribute_count=csr.shape[1],
        presence_count=int(csr.nnz),
        byte_size=arff_path.stat().st_size,
        sha256=_sha256_file(arff_path),
        product_order_checksum=ordered_checksum(mapping["StockCode"]),
        transaction_order_checksum=ordered_checksum(transaction_index["InvoiceNo"]),
    )
    metadata = {
        "relation": relation_name,
        "format": "WEKA sparse ARFF",
        "encoding": "UTF-8",
        "attribute_type": "nominal {0,1}",
        "absent_value": "0 (first nominal value; omitted sparse default)",
        "present_value": "1 (second nominal value; explicitly stored)",
        "positive_value_index_weka": 2,
        "instance_count": result.instance_count,
        "attribute_count": result.attribute_count,
        "presence_count": result.presence_count,
        "file_size_bytes": result.byte_size,
        "sha256": result.sha256,
        "product_order_checksum": result.product_order_checksum,
        "transaction_order_checksum": result.transaction_order_checksum,
        "source_matrix": "data/processed/online_retail_basket_matrix.npz",
        "source_columns": "data/processed/online_retail_basket_columns.json",
        "source_transactions": "data/processed/online_retail_transaction_index.csv",
        "product_mapping": "weka/datasets/product_attribute_mapping.csv",
        "transaction_mapping": "weka/datasets/transaction_row_mapping.csv",
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result


def load_frozen_basket(
    matrix_path: Path, columns_path: Path, transaction_path: Path
) -> tuple[sparse.csr_matrix, pd.DataFrame, pd.DataFrame]:
    """Load the Phase 3 artifacts while preserving their explicit ordering."""
    matrix = sparse.load_npz(matrix_path).tocsr()
    column_document = json.loads(columns_path.read_text(encoding="utf-8"))
    columns = pd.DataFrame(column_document["columns"])
    transactions = pd.read_csv(transaction_path, dtype={"InvoiceNo": "string"})
    return matrix, columns, transactions

