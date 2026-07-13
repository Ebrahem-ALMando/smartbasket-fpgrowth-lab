"""Memory-conscious binary basket matrix construction and export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

from .export import save_csv, save_json


@dataclass(frozen=True)
class BasketArtifacts:
    """Sparse basket matrix plus stable row and column metadata."""

    matrix: sparse.csr_matrix
    transaction_index: pd.DataFrame
    column_metadata: pd.DataFrame


def build_binary_basket_matrix(
    transactions: pd.DataFrame,
    transaction_items: pd.DataFrame,
    product_catalog: pd.DataFrame,
) -> BasketArtifacts:
    """Build a CSR matrix with stable chronological rows and sorted product columns."""
    ordered_transactions = transactions.sort_values(
        ["InvoiceDate", "InvoiceNo"], kind="stable"
    ).reset_index(drop=True)
    transaction_ids = pd.Index(ordered_transactions["InvoiceNo"].astype("string"))
    product_codes = pd.Index(sorted(transaction_items["StockCode"].astype("string").unique()))

    pairs = transaction_items[["InvoiceNo", "StockCode"]].drop_duplicates()
    row_indices = transaction_ids.get_indexer(pairs["InvoiceNo"].astype("string"))
    column_indices = product_codes.get_indexer(pairs["StockCode"].astype("string"))
    if (row_indices < 0).any() or (column_indices < 0).any():
        raise AssertionError("Basket row or column index mapping failed")

    matrix = sparse.coo_matrix(
        (
            np.ones(len(pairs), dtype=np.uint8),
            (row_indices, column_indices),
        ),
        shape=(len(transaction_ids), len(product_codes)),
        dtype=np.uint8,
    ).tocsr()
    matrix.sum_duplicates()
    matrix.data[:] = 1
    matrix.eliminate_zeros()
    if matrix.nnz and not np.all(matrix.data == 1):
        raise AssertionError("Basket matrix is not binary")

    transaction_index = ordered_transactions.copy()
    transaction_index.insert(0, "row_index", np.arange(len(transaction_index), dtype=np.int64))
    catalog = product_catalog.set_index("StockCode")
    column_metadata = pd.DataFrame(
        {
            "column_index": np.arange(len(product_codes), dtype=np.int64),
            "StockCode": product_codes,
            "Description": [catalog.at[code, "Description"] for code in product_codes],
            "ProductLabel": [catalog.at[code, "ProductLabel"] for code in product_codes],
        }
    )
    return BasketArtifacts(matrix, transaction_index, column_metadata)


def save_basket_artifacts(
    artifacts: BasketArtifacts,
    matrix_path: Path,
    columns_path: Path,
    transaction_index_path: Path,
) -> None:
    """Persist CSR data and explicit row/column mappings."""
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    sparse.save_npz(matrix_path, artifacts.matrix, compressed=True)
    save_json(
        {
            "format": "scipy.sparse.csr_matrix",
            "dtype": str(artifacts.matrix.dtype),
            "shape": list(artifacts.matrix.shape),
            "nonzero_entries": int(artifacts.matrix.nnz),
            "columns": artifacts.column_metadata.to_dict(orient="records"),
        },
        columns_path,
    )
    save_csv(artifacts.transaction_index, transaction_index_path)


def to_pandas_sparse_frame(artifacts: BasketArtifacts) -> pd.DataFrame:
    """Create a pandas sparse DataFrame for future mlxtend calls."""
    return pd.DataFrame.sparse.from_spmatrix(
        artifacts.matrix,
        index=artifacts.transaction_index["InvoiceNo"],
        columns=artifacts.column_metadata["StockCode"],
    ).astype(pd.SparseDtype(bool, False))
