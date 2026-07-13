"""Publication-quality Phase 3 data-quality and transaction figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


FIGURE_DPI = 300


def _save_close(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)


def plot_top_products(top_products: pd.DataFrame, path: Path, limit: int = 20) -> None:
    """Plot products ranked by distinct transaction count."""
    data = top_products.head(limit).sort_values("transaction_count")
    labels = data["Description"].str.slice(0, 45)
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(labels, data["transaction_count"], color="#2f6f9f")
    ax.set_title("Top Products by Valid Transaction Frequency")
    ax.set_xlabel("Distinct transaction count")
    ax.set_ylabel("Product description")
    ax.grid(axis="x", alpha=0.25)
    _save_close(fig, path)


def plot_basket_size_distribution(transactions: pd.DataFrame, path: Path) -> None:
    """Plot unique-product basket sizes with a transparent outlier cutoff."""
    sizes = transactions["UniqueProducts"]
    cutoff = max(1, int(np.ceil(sizes.quantile(0.99))))
    displayed = sizes.clip(upper=cutoff)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.hist(displayed, bins=min(50, cutoff), color="#4c956c", edgecolor="white")
    ax.set_title(f"Valid Transaction Basket Sizes (values above P99={cutoff} clipped)")
    ax.set_xlabel("Unique products per transaction")
    ax.set_ylabel("Transaction count")
    ax.grid(axis="y", alpha=0.25)
    _save_close(fig, path)


def plot_transactions_over_time(transactions: pd.DataFrame, path: Path) -> None:
    """Plot weekly valid transaction counts."""
    weekly = (
        transactions.assign(week=transactions["InvoiceDate"].dt.to_period("W").dt.start_time)
        .groupby("week")["InvoiceNo"]
        .nunique()
    )
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(weekly.index, weekly.values, color="#7b2cbf", linewidth=1.6)
    ax.set_title("Valid Transactions over Time")
    ax.set_xlabel("Week")
    ax.set_ylabel("Distinct transaction count")
    ax.grid(alpha=0.25)
    _save_close(fig, path)


def plot_transactions_by_country(country_table: pd.DataFrame, path: Path, limit: int = 15) -> None:
    """Plot the largest country markets and combine the remaining tail."""
    ordered = country_table.sort_values("transaction_count", ascending=False).copy()
    top = ordered.head(limit).copy()
    if len(ordered) > limit:
        other_count = int(ordered.iloc[limit:]["transaction_count"].sum())
        top = pd.concat(
            [
                top,
                pd.DataFrame({"Country": ["Other countries"], "transaction_count": [other_count]}),
            ],
            ignore_index=True,
        )
    top = top.sort_values("transaction_count")
    fig, ax = plt.subplots(figsize=(9, 6.5))
    ax.barh(top["Country"].fillna("Missing"), top["transaction_count"], color="#d97706")
    ax.set_title("Valid Transactions by Country")
    ax.set_xlabel("Distinct transaction count")
    ax.set_ylabel("Country")
    ax.grid(axis="x", alpha=0.25)
    _save_close(fig, path)


def plot_cleaning_impact(lineage: pd.DataFrame, path: Path) -> None:
    """Plot sequentially separated records by primary rejection reason."""
    data = lineage[lineage["removed_or_separated_count"].gt(0)].copy()
    data = data.sort_values("removed_or_separated_count")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(data["step_name"], data["removed_or_separated_count"], color="#b23a48")
    ax.set_title("Cleaning Impact by Primary Rejection Reason")
    ax.set_xlabel("Separated line-item count")
    ax.set_ylabel("Sequential cleaning step")
    ax.grid(axis="x", alpha=0.25)
    _save_close(fig, path)


def plot_missing_profile(missing_table: pd.DataFrame, path: Path) -> None:
    """Plot observed raw missing-value percentages by column."""
    data = missing_table.sort_values("missing_percentage")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.barh(data["column_name"], data["missing_percentage"], color="#457b9d")
    ax.bar_label(bars, fmt="%.2f%%", padding=3, fontsize=8)
    ax.set_title("Raw Workbook Missing-Value Profile")
    ax.set_xlabel("Missing records (%)")
    ax.set_ylabel("Column")
    ax.grid(axis="x", alpha=0.25)
    _save_close(fig, path)


def create_phase3_figures(
    *,
    top_products: pd.DataFrame,
    core_transactions: pd.DataFrame,
    all_transactions: pd.DataFrame,
    country_table: pd.DataFrame,
    lineage: pd.DataFrame,
    missing_table: pd.DataFrame,
    output_directory: Path,
) -> list[Path]:
    """Generate every required Phase 3 static figure."""
    paths = {
        "top": output_directory / "top_products_by_transaction_frequency.png",
        "basket": output_directory / "transaction_basket_size_distribution.png",
        "time": output_directory / "transactions_over_time.png",
        "country": output_directory / "transactions_by_country.png",
        "cleaning": output_directory / "cleaning_impact_by_rejection_reason.png",
        "missing": output_directory / "raw_missing_value_profile.png",
    }
    plot_top_products(top_products, paths["top"])
    plot_basket_size_distribution(core_transactions, paths["basket"])
    plot_transactions_over_time(all_transactions, paths["time"])
    plot_transactions_by_country(country_table, paths["country"])
    plot_cleaning_impact(lineage, paths["cleaning"])
    plot_missing_profile(missing_table, paths["missing"])
    return list(paths.values())
