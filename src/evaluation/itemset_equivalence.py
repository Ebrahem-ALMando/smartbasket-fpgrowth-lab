"""Canonical correctness comparison for frequent-itemset implementations."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from src.mining.itemset_utils import itemset_key


@dataclass(frozen=True)
class EquivalenceSummary:
    """Counts and tolerance evidence for an itemset comparison."""

    common_itemsets: int
    fpgrowth_only_itemsets: int
    apriori_only_itemsets: int
    maximum_support_difference: float
    absolute_tolerance: float
    equivalent: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def compare_itemsets(
    fpgrowth_itemsets: pd.DataFrame,
    apriori_itemsets: pd.DataFrame,
    *,
    absolute_tolerance: float = 1e-12,
) -> tuple[pd.DataFrame, EquivalenceSummary]:
    """Compare canonical itemset keys and support values."""
    def normalize(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
        required = {"support", "itemsets"}
        if not required.issubset(frame.columns):
            raise ValueError(f"{prefix} table lacks support/itemsets columns")
        return pd.DataFrame(
            {
                "itemset_key": frame["itemsets"].map(itemset_key),
                f"{prefix}_support": frame["support"].astype(float),
            }
        ).drop_duplicates("itemset_key")

    left = normalize(fpgrowth_itemsets, "fpgrowth")
    right = normalize(apriori_itemsets, "apriori")
    comparison = left.merge(right, on="itemset_key", how="outer", indicator=True)
    comparison["comparison_status"] = comparison["_merge"].map(
        {"both": "common", "left_only": "fpgrowth_only", "right_only": "apriori_only"}
    )
    comparison["absolute_support_difference"] = (
        comparison["fpgrowth_support"] - comparison["apriori_support"]
    ).abs()
    common = comparison["comparison_status"].eq("common")
    maximum_difference = (
        float(comparison.loc[common, "absolute_support_difference"].max())
        if common.any()
        else 0.0
    )
    fpgrowth_only = int(comparison["comparison_status"].eq("fpgrowth_only").sum())
    apriori_only = int(comparison["comparison_status"].eq("apriori_only").sum())
    summary = EquivalenceSummary(
        common_itemsets=int(common.sum()),
        fpgrowth_only_itemsets=fpgrowth_only,
        apriori_only_itemsets=apriori_only,
        maximum_support_difference=maximum_difference,
        absolute_tolerance=absolute_tolerance,
        equivalent=(
            fpgrowth_only == 0
            and apriori_only == 0
            and maximum_difference <= absolute_tolerance
        ),
    )
    comparison = comparison.drop(columns="_merge").sort_values(
        ["comparison_status", "itemset_key"], kind="mergesort"
    )
    return comparison.reset_index(drop=True), summary
