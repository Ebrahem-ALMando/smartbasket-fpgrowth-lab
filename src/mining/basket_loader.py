"""Load and validate the immutable Phase 3 United Kingdom basket artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import sparse

from src.data.paths import project_path


@dataclass(frozen=True)
class PreparedBasket:
    """Validated sparse basket and its stable row/column metadata."""

    matrix: sparse.csr_matrix
    product_codes: tuple[str, ...]
    descriptions: dict[str, str]
    transaction_index: pd.DataFrame

    @property
    def transaction_count(self) -> int:
        return self.matrix.shape[0]

    @property
    def product_count(self) -> int:
        return self.matrix.shape[1]

    def to_sparse_boolean_frame(self) -> pd.DataFrame:
        """Return an mlxtend-compatible pandas sparse Boolean DataFrame."""
        boolean_matrix = self.matrix.astype(bool, copy=False)
        return pd.DataFrame.sparse.from_spmatrix(
            boolean_matrix,
            index=self.transaction_index["InvoiceNo"].astype(str),
            columns=list(self.product_codes),
        )


def load_prepared_basket() -> PreparedBasket:
    """Load the UK CSR matrix and fail fast on integrity or ordering problems."""
    matrix = sparse.load_npz(
        project_path("data", "processed", "online_retail_basket_matrix.npz")
    ).tocsr()
    metadata = json.loads(
        project_path(
            "data", "processed", "online_retail_basket_columns.json"
        ).read_text(encoding="utf-8")
    )
    transaction_index = pd.read_csv(
        project_path(
            "data", "processed", "online_retail_transaction_index.csv"
        ),
        dtype={"InvoiceNo": "string", "CustomerID": "string"},
    )

    declared_shape = tuple(int(value) for value in metadata["shape"])
    if matrix.shape != declared_shape:
        raise ValueError(f"Matrix shape {matrix.shape} != metadata {declared_shape}")
    if matrix.shape[0] != len(transaction_index):
        raise ValueError("Transaction index length does not match basket rows")
    if matrix.data.size and not np.all(matrix.data == 1):
        raise ValueError("Prepared basket is not binary")
    if metadata.get("format") not in {"csr", "scipy.sparse.csr_matrix"}:
        raise ValueError("Prepared basket metadata does not declare CSR format")
    if int(metadata.get("nonzero_entries", -1)) != matrix.nnz:
        raise ValueError("Nonzero-entry count does not match metadata")

    columns = sorted(metadata["columns"], key=lambda record: record["column_index"])
    expected_indices = list(range(matrix.shape[1]))
    actual_indices = [int(record["column_index"]) for record in columns]
    if actual_indices != expected_indices:
        raise ValueError("Product-column indices are not contiguous and stable")
    product_codes = tuple(str(record["StockCode"]) for record in columns)
    if len(product_codes) != len(set(product_codes)):
        raise ValueError("Product-column metadata contains duplicate codes")
    if product_codes != tuple(sorted(product_codes)):
        raise ValueError("Product columns are no longer in the Phase 3 stable order")
    if transaction_index["row_index"].tolist() != list(range(matrix.shape[0])):
        raise ValueError("Transaction row indices are not contiguous and stable")
    descriptions = {
        str(record["StockCode"]): str(record["Description"]) for record in columns
    }
    return PreparedBasket(matrix, product_codes, descriptions, transaction_index)
