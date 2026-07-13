"""Map WEKA aliases back to the canonical Python StockCode rule format."""

from __future__ import annotations

import json
import math

import pandas as pd

from src.mining.itemset_utils import describe_items, serialize_items
from src.mining.rule_generation import canonical_rule_key
from src.weka.weka_metrics import support_from_count


def canonicalize_weka_rules(
    parsed_rules: pd.DataFrame, product_mapping: pd.DataFrame
) -> pd.DataFrame:
    """Canonicalize valid mappings while retaining invalid rows for audit counts."""
    required = {"arff_attribute", "StockCode", "Description"}
    missing = required.difference(product_mapping.columns)
    if missing:
        raise ValueError(f"Product mapping is missing columns: {sorted(missing)}")
    if product_mapping["arff_attribute"].duplicated().any():
        raise ValueError("Product mapping aliases are not unique")
    alias_to_code = dict(
        zip(product_mapping["arff_attribute"].astype(str), product_mapping["StockCode"].astype(str))
    )
    descriptions = dict(
        zip(product_mapping["StockCode"].astype(str), product_mapping["Description"].fillna("Description unavailable").astype(str))
    )
    rows: list[dict[str, object]] = []
    for rule in parsed_rules.itertuples(index=False):
        premise_aliases = tuple(rule.premise_alias_tuple)
        consequence_aliases = tuple(rule.consequence_alias_tuple)
        unknown = sorted(
            {alias for alias in premise_aliases + consequence_aliases if alias not in alias_to_code}
        )
        mapping_valid = not unknown
        antecedent = tuple(sorted(alias_to_code[a] for a in premise_aliases if a in alias_to_code))
        consequent = tuple(sorted(alias_to_code[a] for a in consequence_aliases if a in alias_to_code))
        premise_count = int(rule.premise_support_count)
        consequence_count = int(rule.consequence_support_count)
        total_count = int(rule.total_support_count)
        transaction_count = int(rule.transaction_count)
        support = support_from_count(total_count, transaction_count)
        conviction_numerator = premise_count * (transaction_count - consequence_count) / transaction_count
        python_denominator = premise_count - total_count
        conviction_python_formula = (
            conviction_numerator / python_denominator if python_denominator else math.inf
        )
        conviction_weka_formula = conviction_numerator / (python_denominator + 1)
        rows.append(
            {
                "weka_rule_index": int(rule.rule_index),
                "weka_rule_text": rule.weka_rule_text,
                "original_premise_aliases": rule.premise_aliases,
                "original_consequence_aliases": rule.consequence_aliases,
                "mapping_valid": mapping_valid,
                "unknown_aliases": json.dumps(unknown),
                "rule_key": canonical_rule_key(antecedent, consequent) if mapping_valid else None,
                "antecedent_codes": serialize_items(antecedent),
                "antecedent_descriptions": json.dumps(describe_items(antecedent, descriptions), ensure_ascii=False),
                "consequent_codes": serialize_items(consequent),
                "consequent_descriptions": json.dumps(describe_items(consequent, descriptions), ensure_ascii=False),
                "antecedent_length": len(antecedent),
                "consequent_length": len(consequent),
                "premise_support_count": int(rule.premise_support_count),
                "consequence_support_count": int(rule.consequence_support_count),
                "support_count": int(rule.total_support_count),
                "transaction_count": int(rule.transaction_count),
                "support": support,
                "support_source": "derived_from_weka_api_counts",
                "confidence": float(rule.confidence),
                "lift": float(rule.lift),
                "leverage": float(rule.leverage),
                "conviction": float(rule.conviction),
                "conviction_weka_formula_from_counts": conviction_weka_formula,
                "conviction_python_formula_from_counts": conviction_python_formula,
                "conviction_definition_note": (
                    "WEKA 3.8.7 adds +1 to (premise_support_count-total_support_count); "
                    "Python/mlxtend uses the unsmoothed denominator"
                ),
                "primary_metric_name": rule.primary_metric_name,
                "primary_metric_value": float(rule.primary_metric_value),
                "metric_names": rule.metric_names,
                "metric_values": rule.metric_values,
            }
        )
    return pd.DataFrame(rows)
