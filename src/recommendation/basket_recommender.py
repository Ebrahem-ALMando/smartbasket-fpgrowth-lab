"""Evidence-ranked, non-personalized basket recommendation simulator."""

from __future__ import annotations

import json

import ipywidgets as widgets
import pandas as pd
from IPython.display import HTML, display

from src.data.export import save_csv
from src.data.paths import project_path
from src.mining.basket_loader import load_prepared_basket
from src.recommendation.recommendation_explanations import recommendation_explanation


RECOMMENDATION_COLUMNS = [
    "recommended_product_code",
    "recommended_product_description",
    "matching_rule",
    "support",
    "support_count",
    "confidence",
    "lift",
    "stability_presence_rate",
    "stability_category",
    "evidence_tier",
    "matching_rule_count",
    "explanation",
]


class BasketRecommender:
    """Match qualified rule antecedents and rank consequents lexicographically."""

    def __init__(self, rules: pd.DataFrame, catalog: dict[str, str]) -> None:
        self.catalog = dict(catalog)
        self.rules = rules.loc[
            rules.evidence_tier.isin(["Tier A", "Tier B"])
            & rules.rule_presence_rate.ge(0.50)
            & ~rules.is_logically_redundant
            & ~rules.insufficient_business_evidence
        ].copy()
        self.rules["antecedent_set"] = self.rules.antecedent_codes.map(
            lambda value: frozenset(json.loads(value))
        )
        self.rules["consequent_tuple"] = self.rules.consequent_codes.map(
            lambda value: tuple(json.loads(value))
        )

    @classmethod
    def from_outputs(cls) -> "BasketRecommender":
        rules = pd.read_csv(
            project_path("outputs", "tables", "rule_quality_audit.csv")
        )
        return cls(rules, load_prepared_basket().descriptions)

    def resolve_product(self, query: str) -> tuple[str, ...]:
        """Resolve an exact code or description substring to stable product codes."""
        cleaned = query.strip()
        if cleaned in self.catalog:
            return (cleaned,)
        folded = cleaned.casefold()
        matches = tuple(
            sorted(
                code
                for code, description in self.catalog.items()
                if folded and folded in description.casefold()
            )
        )
        if not matches:
            raise ValueError(f"No product matches: {query}")
        return matches

    def recommend(
        self, basket_codes: list[str] | tuple[str, ...] | set[str], *, maximum_results: int = 10
    ) -> pd.DataFrame:
        """Return best qualified rule evidence per unseen consequent product."""
        basket = frozenset(str(code) for code in basket_codes)
        unknown = sorted(basket.difference(self.catalog))
        if unknown:
            raise ValueError(f"Unknown product codes: {unknown}")
        matching = self.rules.loc[
            self.rules["antecedent_set"].map(lambda antecedent: antecedent.issubset(basket))
        ].copy()
        if matching.empty:
            return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)
        matching["tier_rank"] = matching.evidence_tier.map({"Tier A": 0, "Tier B": 1})
        matching = matching.sort_values(
            ["tier_rank", "rule_presence_rate", "confidence", "lift", "support_count", "rule_key"],
            ascending=[True, False, False, False, False, True],
            kind="mergesort",
        )
        rows = []
        for rule in matching.itertuples(index=False):
            for product in rule.consequent_tuple:
                if product in basket:
                    continue
                rows.append(
                    {
                        "recommended_product_code": product,
                        "recommended_product_description": self.catalog.get(product, "Description unavailable"),
                        "matching_rule": rule.rule_key,
                        "support": rule.support,
                        "support_count": rule.support_count,
                        "confidence": rule.confidence,
                        "lift": rule.lift,
                        "stability_presence_rate": rule.rule_presence_rate,
                        "stability_category": rule.stability_category,
                        "evidence_tier": rule.evidence_tier,
                        "tier_rank": rule.tier_rank,
                        "explanation": recommendation_explanation(
                            rule_key=rule.rule_key,
                            confidence=rule.confidence,
                            lift=rule.lift,
                            presence_rate=rule.rule_presence_rate,
                            evidence_tier=rule.evidence_tier,
                        ),
                    }
                )
        if not rows:
            return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)
        evidence = pd.DataFrame(rows).drop_duplicates(
            ["recommended_product_code", "matching_rule"]
        )
        evidence["matching_rule_count"] = evidence.groupby(
            "recommended_product_code"
        )["matching_rule"].transform("size")
        ranked = evidence.sort_values(
            ["tier_rank", "stability_presence_rate", "confidence", "lift", "support_count", "recommended_product_code", "matching_rule"],
            ascending=[True, False, False, False, False, True, True],
            kind="mergesort",
        ).drop_duplicates("recommended_product_code")
        return ranked.drop(columns="tier_rank")[RECOMMENDATION_COLUMNS].head(maximum_results).reset_index(drop=True)


def build_recommender_widget(recommender: BasketRecommender | None = None) -> widgets.Widget:
    """Return a Jupyter interface with explicit no-result and warning behavior."""
    recommender = recommender or BasketRecommender.from_outputs()
    text = widgets.Text(
        description="Basket codes",
        placeholder="Comma-separated product codes, e.g. 21801, 21802",
        layout=widgets.Layout(width="80%"),
    )
    button = widgets.Button(description="Find associations", button_style="info")
    output = widgets.Output()

    def run(_: object) -> None:
        with output:
            output.clear_output(wait=True)
            codes = [value.strip() for value in text.value.split(",") if value.strip()]
            try:
                recommendations = recommender.recommend(codes)
            except ValueError as exc:
                display(HTML(f"<b>Input error:</b> {exc}"))
                return
            if recommendations.empty:
                display(HTML("<b>No evidence-qualified recommendation exists for this basket.</b> Nothing was fabricated."))
            else:
                display(HTML("<p>Rule-based, non-personalized suggestions; associations are not causal predictions.</p>"))
                display(recommendations)

    button.on_click(run)
    return widgets.VBox([widgets.HTML("<h3>Rule-based Basket Recommendation Simulator</h3>"), text, button, output])


def export_recommendation_outputs() -> dict[str, object]:
    """Generate actual examples and a portable client-side simulator."""
    recommender = BasketRecommender.from_outputs()
    examples = []
    seen_baskets: set[tuple[str, ...]] = set()
    for row in recommender.rules.itertuples(index=False):
        basket = tuple(sorted(row.antecedent_set))
        if basket in seen_baskets:
            continue
        seen_baskets.add(basket)
        recommendations = recommender.recommend(basket, maximum_results=3)
        for rank, recommendation in enumerate(recommendations.itertuples(index=False), start=1):
            examples.append(
                {
                    "example_id": len(seen_baskets),
                    "input_basket_codes": json.dumps(basket),
                    "input_basket_descriptions": json.dumps([recommender.catalog[code] for code in basket], ensure_ascii=False),
                    "recommendation_rank": rank,
                    **recommendation._asdict(),
                }
            )
        if len(seen_baskets) >= 10:
            break
    example_frame = pd.DataFrame(examples)
    save_csv(
        example_frame,
        project_path("outputs", "tables", "recommendation_examples.csv"),
    )
    fields = ["rule_key", "antecedent_codes", "consequent_codes", "support", "support_count", "confidence", "lift", "rule_presence_rate", "stability_category", "evidence_tier"]
    rules_json = recommender.rules[fields].to_json(orient="records")
    catalog_json = json.dumps(recommender.catalog, ensure_ascii=False).replace("</", "<\\/")
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Basket Recommendation Simulator</title>
<style>body{{font-family:system-ui;margin:2rem;color:#0f172a}} input{{width:75%;padding:.6rem}} button{{padding:.6rem}} table{{border-collapse:collapse;width:100%;margin-top:1rem}} td,th{{border-bottom:1px solid #ddd;padding:.4rem;text-align:left}} .warn{{background:#fef3c7;padding:1rem}}</style></head><body>
<h1>Rule-based Basket Recommendation Simulator</h1><p class='warn'>Educational, non-personalized, non-causal. Enter comma-separated product codes. The tool returns no result when evidence is insufficient.</p>
<input id='basket' placeholder='Example: 21801, 21802'><button id='run'>Find associations</button><div id='result'></div>
<script>const rules={rules_json}; const catalog={catalog_json}; run.onclick=()=>{{let basketSet=new Set(basket.value.split(',').map(x=>x.trim()).filter(Boolean)); let unknown=[...basketSet].filter(x=>!catalog[x]); if(unknown.length){{result.innerHTML='<p>Unknown codes: '+unknown.join(', ')+'</p>';return;}}
let rows=[]; rules.forEach(r=>{{let a=JSON.parse(r.antecedent_codes),c=JSON.parse(r.consequent_codes); if(a.every(x=>basketSet.has(x))) c.filter(x=>!basketSet.has(x)).forEach(product=>rows.push({{product,...r}}));}}); rows.sort((x,y)=>x.evidence_tier.localeCompare(y.evidence_tier)||y.rule_presence_rate-x.rule_presence_rate||y.confidence-x.confidence||y.lift-x.lift||y.support_count-x.support_count||x.product.localeCompare(y.product)); let best=[]; let used=new Set(); rows.forEach(r=>{{if(!used.has(r.product)){{used.add(r.product);best.push(r);}}}}); best=best.slice(0,10); if(!best.length){{result.innerHTML='<p><b>No evidence-qualified recommendation.</b> Nothing was fabricated.</p>';return;}} result.innerHTML='<table><tr><th>Product</th><th>Rule</th><th>Count</th><th>Confidence</th><th>Lift</th><th>Presence</th><th>Tier</th></tr>'+best.map(r=>`<tr><td>${{r.product}} — ${{catalog[r.product]}}</td><td>${{r.rule_key}}</td><td>${{r.support_count}}</td><td>${{r.confidence.toFixed(3)}}</td><td>${{r.lift.toFixed(3)}}</td><td>${{r.rule_presence_rate.toFixed(2)}}</td><td>${{r.evidence_tier}}</td></tr>`).join('')+'</table><p>These are associations requiring validation, not purchase probabilities.</p>';}};</script></body></html>"""
    path = project_path(
        "outputs", "interactive", "basket_recommendation_simulator.html"
    )
    path.write_text(html, encoding="utf-8")
    return {"qualified_rules": len(recommender.rules), "example_rows": len(example_frame), "html_bytes": path.stat().st_size}


if __name__ == "__main__":
    print(export_recommendation_outputs())
