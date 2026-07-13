"""Cached rule filtering for Jupyter widgets and a self-contained HTML explorer."""

from __future__ import annotations

import json

import ipywidgets as widgets
import pandas as pd
import plotly.graph_objects as go
from IPython.display import HTML, display
from plotly.offline import get_plotlyjs

from src.data.export import save_csv
from src.data.paths import project_path


def filter_explorer_rules(
    rules: pd.DataFrame,
    *,
    minimum_support: float = 0.005,
    minimum_confidence: float = 0.70,
    minimum_lift: float = 1.20,
    stability_category: str = "All",
    evidence_tier: str = "All",
    maximum_antecedent_length: int = 2,
    maximum_rules: int = 100,
) -> pd.DataFrame:
    """Filter precomputed rules and return stable lexicographic evidence order."""
    mask = (
        rules.support.ge(minimum_support)
        & rules.confidence.ge(minimum_confidence)
        & rules.lift.ge(minimum_lift)
        & rules.antecedent_length.le(maximum_antecedent_length)
    )
    if stability_category != "All":
        mask &= rules.stability_category.eq(stability_category)
    if evidence_tier != "All":
        mask &= rules.evidence_tier.eq(evidence_tier)
    filtered = rules.loc[mask].copy()
    filtered["_tier_rank"] = filtered.evidence_tier.map(
        {"Tier A": 0, "Tier B": 1, "Tier C": 2, "Tier D": 3}
    ).fillna(9)
    return filtered.sort_values(
        ["_tier_rank", "rule_presence_rate", "confidence", "lift", "support_count", "rule_key"],
        ascending=[True, False, False, False, False, True],
        kind="mergesort",
    ).drop(columns="_tier_rank").head(maximum_rules).reset_index(drop=True)


def _widget_figure(filtered: pd.DataFrame) -> go.Figure:
    return go.Figure(
        go.Scatter(
            x=filtered.support,
            y=filtered.confidence,
            mode="markers",
            marker=dict(color=filtered.lift, colorscale="Viridis", showscale=True, colorbar=dict(title="Lift")),
            text=filtered.rule_key,
            hovertemplate="%{text}<br>Support=%{x:.4f}<br>Confidence=%{y:.3f}<extra></extra>",
        )
    ).update_layout(
        title="Precomputed matching rules",
        xaxis_title="Support",
        yaxis_title="Confidence",
        template="plotly_white",
        height=430,
    )


def build_threshold_explorer_widget(rules: pd.DataFrame | None = None) -> widgets.Widget:
    """Return an ipywidgets explorer that never invokes mining."""
    if rules is None:
        rules = pd.read_csv(project_path("outputs", "tables", "rule_quality_audit.csv"))
    support = widgets.FloatSlider(value=0.005, min=0.005, max=0.03, step=0.001, description="Support")
    confidence = widgets.FloatSlider(value=0.70, min=0.70, max=0.95, step=0.01, description="Confidence")
    lift = widgets.FloatSlider(value=1.20, min=1.0, max=20.0, step=0.2, description="Lift")
    stability = widgets.Dropdown(options=["All", "Very stable", "Moderately stable", "Weakly stable", "Unstable"], description="Stability")
    tier = widgets.Dropdown(options=["All", "Tier A", "Tier B", "Tier C", "Tier D"], description="Evidence")
    antecedent_length = widgets.IntSlider(value=2, min=1, max=2, description="Antecedent")
    maximum = widgets.IntSlider(value=50, min=10, max=200, step=10, description="Max rules")
    output = widgets.Output()

    def update(*_: object) -> None:
        filtered = filter_explorer_rules(
            rules,
            minimum_support=support.value,
            minimum_confidence=confidence.value,
            minimum_lift=lift.value,
            stability_category=stability.value,
            evidence_tier=tier.value,
            maximum_antecedent_length=antecedent_length.value,
            maximum_rules=maximum.value,
        )
        with output:
            output.clear_output(wait=True)
            near_floor = int(filtered.support_count.le(112).sum()) if not filtered.empty else 0
            display(HTML(f"<b>{len(filtered)} displayed rules</b>; {near_floor} near the support floor. Filtering is precomputed and non-causal."))
            if not filtered.empty:
                display(_widget_figure(filtered))
                display(filtered[["rule_key", "support_count", "confidence", "lift", "rule_presence_rate", "stability_category", "evidence_tier"]].head(20))
            else:
                display(HTML("<i>No rules match these controls.</i>"))

    for control in [support, confidence, lift, stability, tier, antecedent_length, maximum]:
        control.observe(update, names="value")
    update()
    return widgets.VBox([
        widgets.HTML("<h3>Threshold Explorer</h3><p>Filters cached Phase 5 rules; it does not rerun FP-Growth.</p>"),
        widgets.HBox([support, confidence, lift]),
        widgets.HBox([stability, tier, antecedent_length, maximum]),
        output,
    ])


def export_threshold_explorer() -> dict[str, object]:
    """Write presets and a client-side self-contained Plotly rule explorer."""
    rules = pd.read_csv(project_path("outputs", "tables", "rule_quality_audit.csv"))
    presets = pd.DataFrame(
        [
            {"preset": "Evidence focused", "minimum_support": 0.0075, "minimum_confidence": 0.80, "minimum_lift": 2.0, "stability_category": "Very stable", "evidence_tier": "Tier A", "maximum_antecedent_length": 2, "maximum_rules": 50},
            {"preset": "Balanced review", "minimum_support": 0.005, "minimum_confidence": 0.70, "minimum_lift": 1.2, "stability_category": "All", "evidence_tier": "Tier A", "maximum_antecedent_length": 2, "maximum_rules": 100},
            {"preset": "Stability audit", "minimum_support": 0.005, "minimum_confidence": 0.70, "minimum_lift": 1.2, "stability_category": "Weakly stable", "evidence_tier": "All", "maximum_antecedent_length": 2, "maximum_rules": 100},
        ]
    )
    save_csv(presets, project_path("outputs", "tables", "threshold_explorer_presets.csv"))
    fields = ["rule_key", "support", "support_count", "confidence", "lift", "rule_presence_rate", "stability_category", "evidence_tier", "antecedent_length", "quality_flags"]
    data = rules[fields].to_dict("records")
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    plotly_js = get_plotlyjs()
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Threshold Explorer</title>
<script>{plotly_js}</script><style>body{{font-family:system-ui;margin:1.5rem;color:#0f172a}} .controls{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}} label{{display:flex;flex-direction:column}} #table{{max-height:420px;overflow:auto}} table{{border-collapse:collapse;width:100%;font-size:.85rem}} td,th{{border-bottom:1px solid #ddd;padding:.35rem;text-align:left}} .warn{{background:#fef3c7;padding:.7rem}}</style></head>
<body><h1>Precomputed Rule Threshold Explorer</h1><p>This educational aid filters saved Phase 5 rules and never reruns mining. Associations are non-causal.</p>
<div class='controls'>
<label>Minimum Support <input id='support' type='number' value='0.005' min='0.005' step='0.001'></label>
<label>Minimum Confidence <input id='confidence' type='number' value='0.70' min='0.70' max='1' step='0.01'></label>
<label>Minimum Lift <input id='lift' type='number' value='1.20' min='1' step='0.1'></label>
<label>Stability <select id='stability'><option>All</option><option>Very stable</option><option>Moderately stable</option><option>Weakly stable</option><option>Unstable</option></select></label>
<label>Evidence tier <select id='tier'><option>All</option><option>Tier A</option><option>Tier B</option><option>Tier C</option><option>Tier D</option></select></label>
<label>Maximum antecedent length <input id='alen' type='number' value='2' min='1' max='2'></label>
<label>Maximum displayed rules <input id='maximum' type='number' value='100' min='10' max='500' step='10'></label></div>
<p id='summary' class='warn'></p><div id='scatter'></div><div id='liftplot'></div><div id='stabilityplot'></div><div id='table'></div>
<script>const rules={data_json}; const ids=['support','confidence','lift','stability','tier','alen','maximum']; ids.forEach(id=>document.getElementById(id).addEventListener('input',update));
function update(){{let s=+support.value,c=+confidence.value,l=+lift.value,a=+alen.value,m=+maximum.value,st=stability.value,t=tier.value;
let f=rules.filter(r=>r.support>=s&&r.confidence>=c&&r.lift>=l&&r.antecedent_length<=a&&(st==='All'||r.stability_category===st)&&(t==='All'||r.evidence_tier===t));
f.sort((x,y)=>x.evidence_tier.localeCompare(y.evidence_tier)||y.rule_presence_rate-x.rule_presence_rate||y.confidence-x.confidence||y.lift-x.lift||x.rule_key.localeCompare(y.rule_key)); let shown=f.slice(0,m); let near=f.filter(r=>r.support_count<=112).length;
summary.textContent=`${{f.length}} matching rules; displaying ${{shown.length}}. ${{near}} are near the frozen support floor. Metrics do not prove causation or usefulness.`;
Plotly.react('scatter',[{{x:shown.map(r=>r.support),y:shown.map(r=>r.confidence),text:shown.map(r=>r.rule_key),mode:'markers',marker:{{color:shown.map(r=>r.lift),colorscale:'Viridis',showscale:true,colorbar:{{title:'Lift'}}}},hovertemplate:'%{{text}}<br>Support=%{{x:.4f}}<br>Confidence=%{{y:.3f}}<extra></extra>'}}],{{title:'Support versus Confidence',xaxis:{{title:'Support'}},yaxis:{{title:'Confidence'}}}});
Plotly.react('liftplot',[{{x:shown.map(r=>r.lift),type:'histogram'}}],{{title:'Lift distribution',xaxis:{{title:'Lift'}}}}); let counts={{}}; shown.forEach(r=>counts[r.stability_category]=(counts[r.stability_category]||0)+1); Plotly.react('stabilityplot',[{{x:Object.keys(counts),y:Object.values(counts),type:'bar'}}],{{title:'Stability distribution'}});
table.innerHTML='<table><thead><tr><th>Rule</th><th>Count</th><th>Confidence</th><th>Lift</th><th>Presence</th><th>Tier</th></tr></thead><tbody>'+shown.map(r=>`<tr><td>${{r.rule_key}}</td><td>${{r.support_count}}</td><td>${{r.confidence.toFixed(3)}}</td><td>${{r.lift.toFixed(3)}}</td><td>${{r.rule_presence_rate.toFixed(2)}}</td><td>${{r.evidence_tier}}</td></tr>`).join('')+'</tbody></table>';}} update();</script></body></html>"""
    path = project_path("outputs", "interactive", "threshold_explorer.html")
    path.write_text(html, encoding="utf-8")
    return {"rules_available": len(rules), "preset_count": len(presets), "html_bytes": path.stat().st_size}


if __name__ == "__main__":
    print(export_threshold_explorer())
