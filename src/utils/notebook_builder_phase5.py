"""Build Arabic-first Phase 5 stability, interactive, and business notebooks."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

from src.data.paths import ensure_directory
from src.utils.notebook_builder import KERNEL_METADATA


def _markdown(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text.strip())


def _code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(source.strip())


def build_rule_quality_notebook() -> nbf.NotebookNode:
    """Create Notebook 06 from saved Bootstrap evidence and reusable audits."""
    notebook = nbf.v4.new_notebook(metadata=KERNEL_METADATA.copy())
    notebook.cells = [
        _markdown(
            """
# 06 — جودة القواعد واستقرارها الإحصائي

لا تكفي قوة Support أوConfidence أوLift لإثبات أن القاعدة مستقرة أو مفيدة. يعرض هذا Notebook Bootstrap transaction resampling، وعدم اليقين، والأعلام المضللة، وRedundancy وEvidence tiers. الاستقرار تجريبي تحت هذه البيانات والعتبات، وليس برهاناً عاماً أو سببياً.
"""
        ),
        _code(
            """
from pathlib import Path
import sys
import pandas as pd
from IPython.display import Image, display

from src.data.paths import PROJECT_ROOT, project_path
from src.evaluation.rule_quality import build_rule_quality_outputs
from src.visualization.advanced_results import generate_advanced_figures

assert Path.cwd().resolve() == PROJECT_ROOT
assert ".venv" in sys.executable
summary = pd.read_csv(project_path("outputs", "tables", "bootstrap_summary.csv"))
metadata = pd.read_csv(project_path("outputs", "tables", "bootstrap_run_metadata.csv"))
assert len(metadata) == int(summary.loc[0, "resamples_requested"])
assert metadata.status.str.startswith("success").all()
display(summary)
"""
        ),
        _markdown(
            """
## منهج Bootstrap والبذور

سُحبت كل عينة من 17,901 معاملة مع الإرجاع وبالحجم نفسه. استخدمت البذور المتسلسلة المسجلة في metadata، وMinimum Support=0.005، وsupport count=90، و`max_len=3`. تُعد القاعدة حاضرة فقط إذا عادت بالمفتاح نفسه ومرت أيضاً بـConfidence≥0.70 وLift≥1.20. تحفظ المقاييس عند إمكان توليد المفتاح حتى لو لم يمر بكل الحدود.
"""
        ),
        _code(
            """
display(metadata[["resample_id", "seed", "sample_size", "unique_source_transactions", "minimum_support_count", "frequent_itemset_count", "candidate_rules_present", "runtime_seconds", "status"]])
print("Recorded seeds:", metadata.seed.tolist())
"""
        ),
        _markdown("## فئات الاستقرار وRule Presence"),
        _code(
            """
categories = pd.read_csv(project_path("outputs", "tables", "rule_stability_categories.csv"))
stability = pd.read_csv(project_path("outputs", "tables", "rule_stability_results.csv"))
display(categories)
display(stability[["rule_key", "support_count", "confidence", "lift", "rule_presence_rate", "stability_category"]].head(15))
"""
        ),
        _markdown(
            """
Very stable تعني حضوراً≥0.80، وModerately stable من 0.50، وWeakly stable من 0.20، وUnstable دون 0.20. هذه حدود اصطلاحية للمشروع وليست قوانين علمية.
"""
        ),
        _markdown("## عدم اليقين في المقاييس"),
        _code(
            """
uncertainty = pd.read_csv(project_path("outputs", "tables", "rule_metric_uncertainty.csv"))
display(uncertainty.head(15))
display(stability[["rule_key", "confidence_mean", "confidence_p025", "confidence_p975", "lift_mean", "lift_p025", "lift_p975"]].head(12))
"""
        ),
        _markdown("## Stable وUnstable examples"),
        _code(
            """
stable_examples = stability.nlargest(8, ["rule_presence_rate", "support_count"])
unstable_examples = stability.nsmallest(8, ["rule_presence_rate", "support_count"])
display(stable_examples[["rule_key", "support_count", "confidence", "lift", "rule_presence_rate", "stability_category"]])
display(unstable_examples[["rule_key", "support_count", "confidence", "lift", "rule_presence_rate", "stability_category"]])
"""
        ),
        _markdown("## Misleading-rule detection وRedundancy"),
        _code(
            """
quality_result = build_rule_quality_outputs()
flags = pd.read_csv(project_path("outputs", "tables", "misleading_rule_flags.csv"))
redundant = pd.read_csv(project_path("outputs", "tables", "redundant_rules.csv"))
display(pd.DataFrame([quality_result]))
display(flags)
display(redundant.head(12))
"""
        ),
        _markdown(
            """
توضح الأعلام حالات مثل Lift مرتفع قرب floor أو Consequent شائع أو استقرار ضعيف؛ لا تعلن تلقائياً بطلان القاعدة. تعد القاعدة الأطول redundant فقط إذا وجدت قاعدة أبسط لنفس Consequent بفارق Confidence≤0.05 ومن دون تحسن Lift يتجاوز 10%.
"""
        ),
        _markdown("## Evidence tiers والمرشحون النهائيون"),
        _code(
            """
tiers = pd.read_csv(project_path("outputs", "tables", "rule_evidence_tiers.csv"))
final_candidates = pd.read_csv(project_path("outputs", "tables", "final_interpretation_candidates.csv"))
display(tiers)
display(final_candidates[["rule_key", "support_count", "confidence", "lift", "rule_presence_rate", "evidence_tier", "recommended_disposition", "quality_flags"]].head(15))
"""
        ),
        _markdown("## Corrected scalability"),
        _code(
            """
scalability = pd.read_csv(project_path("outputs", "comparisons", "scalability_protocol_summary.csv"))
display(scalability[["protocol", "subset_fraction", "algorithm", "support_proportion", "support_count", "median_runtime_seconds", "median_itemset_count"]])
"""
        ),
        _markdown(
            """
Protocol A يثبت النسبة فتتغير قيمة count، بينما Protocol B يثبت count=90 فتتغير النسبة. يستخدم كلاهما ثلاثة random seeds للكسور دون 100% والصفوف نفسها للخوارزميتين. لا يحذف ذلك anomaly الأصلي؛ بل يفسره بوصفه أثراً للحد العددي والتركيب الزمني.
"""
        ),
        _markdown("## رسوم متقدمة مختارة"),
        _code(
            """
generate_advanced_figures()
for filename in [
    "rule_stability_category_distribution.png",
    "confidence_uncertainty_top_stable_rules.png",
    "misleading_rule_flag_counts.png",
    "corrected_scalability_comparison.png",
]:
    display(Image(filename=str(project_path("outputs", "figures", filename)), width=900))
"""
        ),
        _markdown(
            """
## القيود

Bootstrap يعيد أخذ العينات من dataset نفسه ولا يثبت الصلاحية خارجياً. الفواصل empirical وليست ضمانات سكانية، و20 resamples تعطي دقة محدودة لمعدل الحضور. لم تنفذ WEKA أو سببية أو اختبار أثر تجاري.
"""
        ),
    ]
    return notebook


def build_interactive_notebook() -> nbf.NotebookNode:
    """Create Notebook 07 with cached widgets and portable HTML links."""
    notebook = nbf.v4.new_notebook(metadata=KERNEL_METADATA.copy())
    notebook.cells = [
        _markdown(
            """
# 07 — المختبر التفاعلي للقواعد المستقرة

تستخدم الأدوات نتائج Phase 5 المسبقة ولا تعيد تعدين البيانات عند تحريك slider. هي أدوات تعليمية تحليلية، وليست نظام قرار تجاري أو Personalized Recommender أو نموذجاً سببياً.
"""
        ),
        _code(
            """
from pathlib import Path
import sys
import pandas as pd
from IPython.display import FileLink, Image, display

from src.data.paths import PROJECT_ROOT, project_path
from src.recommendation.basket_recommender import BasketRecommender, build_recommender_widget, export_recommendation_outputs
from src.visualization.network_export import export_product_network
from src.visualization.threshold_explorer import build_threshold_explorer_widget, export_threshold_explorer

assert Path.cwd().resolve() == PROJECT_ROOT
assert ".venv" in sys.executable
"""
        ),
        _markdown("## Threshold Explorer"),
        _code(
            """
threshold_export = export_threshold_explorer()
display(build_threshold_explorer_widget())
threshold_export
"""
        ),
        _markdown(
            """
يعرض Explorer Support وConfidence وLift والاستقرار وEvidence tier وأطوال المقدمات وحد العرض. النسخة HTML تعمل client-side على القواعد المحفوظة؛ لا تقدم إعادة تعدين ديناميكية أو خادماً.
"""
        ),
        _markdown("## Stable Product Association Network"),
        _code(
            """
network_result = export_product_network()
display(pd.DataFrame([network_result]))
display(Image(filename=str(project_path("outputs", "figures", "product_network_preview.png")), width=950))
display(pd.read_csv(project_path("outputs", "tables", "product_network_summary.csv")))
"""
        ),
        _markdown(
            """
تعرض الشبكة قواعد one-to-one مستقرة وغير redundant من Tier A/B فقط، بحد أقصى 40 عقدة و60 حافة. الاتجاه Association direction وليس سببية، والمركزية وصفية وليست أهمية مالية.
"""
        ),
        _markdown("## Rule-based Basket Recommendation Simulator"),
        _code(
            """
recommendation_export = export_recommendation_outputs()
recommender = BasketRecommender.from_outputs()
display(build_recommender_widget(recommender))
display(pd.read_csv(project_path("outputs", "tables", "recommendation_examples.csv")).head(12))
recommendation_export
"""
        ),
        _markdown(
            """
يطابق simulator القواعد التي يكون Antecedent فيها subset من السلة، ويستبعد المنتجات الموجودة أصلاً. يرتب حسب Evidence tier ثم Bootstrap presence وConfidence وLift وcount. يمكنه إعادة **لا توجد توصية مؤهلة** ولا يخترع ناتجاً. التفسير يعرض المقاييس الفعلية ويحذر من السببية والتخصيص.
"""
        ),
        _markdown("## روابط HTML المحمولة"),
        _code(
            """
for relative in [
    Path("outputs/interactive/threshold_explorer.html"),
    Path("outputs/interactive/product_association_network.html"),
    Path("outputs/interactive/basket_recommendation_simulator.html"),
]:
    assert project_path(*relative.parts).exists()
    display(FileLink(str(relative)))
"""
        ),
        _markdown(
            """
## إعادة تشغيل Widgets والقيود

بعد Restart Kernel شغّل **Run All** لإعادة إنشاء widgets؛ لا يلزم تعديل الخلايا. HTML مستقلة لكنها precomputed. الأدوات غير شخصية، ولا تستخدم CustomerID، ولا تتنبأ بأن العميل سيشتري Consequent، ولا تقيس أثر الإيراد.
"""
        ),
    ]
    return notebook


def build_business_notebook() -> nbf.NotebookNode:
    """Create Notebook 09 for cautious, traceable business candidates."""
    notebook = nbf.v4.new_notebook(metadata=KERNEL_METADATA.copy())
    notebook.cells = [
        _markdown(
            """
# 09 — من القواعد الخام إلى مرشحات إجراءات أعمال

يحول هذا Notebook القواعد المدققة إلى **candidates requiring controlled validation**. لا يدعي زيادة إيراد أو سببية أو أن العملاء سيشترون Consequent أو أن تغيير الرفوف تدخل مثبت.
"""
        ),
        _code(
            """
from pathlib import Path
import sys
import pandas as pd
from IPython.display import Image, display

from src.data.paths import PROJECT_ROOT, project_path
from src.recommendation.business_actions import generate_business_actions

assert Path.cwd().resolve() == PROJECT_ROOT
assert ".venv" in sys.executable
action_counts = generate_business_actions()
pd.DataFrame([action_counts])
"""
        ),
        _markdown("## Funnel الأدلة"),
        _code(
            """
tiers = pd.read_csv(project_path("outputs", "tables", "rule_evidence_tiers.csv"))
quality = pd.read_csv(project_path("outputs", "tables", "rule_quality_audit.csv"))
final_candidates = pd.read_csv(project_path("outputs", "tables", "final_interpretation_candidates.csv"))
display(tiers)
print(f"Phase 4 candidates: {len(quality):,}; evidence-qualified final candidates: {len(final_candidates):,}")
display(final_candidates[["rule_key", "support_count", "confidence", "lift", "rule_presence_rate", "evidence_tier", "quality_flags"]].head(15))
"""
        ),
        _markdown("## تفسير Product Network"),
        _code(
            """
display(Image(filename=str(project_path("outputs", "figures", "product_network_preview.png")), width=950))
display(pd.read_csv(project_path("outputs", "tables", "product_network_summary.csv")))
"""
        ),
        _markdown(
            """
الشبكة تلخص عينة مقروءة من العلاقات المستقرة one-to-one. الدرجة أو المكون لا يعنيان أهمية مالية أو سبباً للشراء؛ هما وصف لبنية القواعد المختارة.
"""
        ),
        _markdown("## منهج Business Action Generator"),
        _code(
            """
actions = pd.read_csv(project_path("outputs", "tables", "business_action_candidates.csv"))
action_summary = pd.read_csv(project_path("outputs", "tables", "business_action_summary.csv"))
display(action_summary)
"""
        ),
        _markdown("## Bundle وCross-sell وCo-display candidates"),
        _code(
            """
for category in ["Product bundle candidate", "Cross-sell candidate", "Co-display candidate"]:
    print(category)
    display(actions.loc[actions.action_category.eq(category), ["rule_key", "support_count", "confidence", "lift", "rule_presence_rate", "evidence_tier", "suggested_validation_step"]].head(8))
"""
        ),
        _markdown("## مرشحون للمراقبة وحالات مرفوضة"),
        _code(
            """
more = pd.read_csv(project_path("outputs", "tables", "rules_requiring_more_evidence.csv"))
display(more.loc[more.action_category.eq("Monitor for more evidence")].head(8))
display(more.loc[more.action_category.eq("Reject from commercial interpretation")].head(8))
"""
        ),
        _markdown(
            """
## حدود الاستدلال والتحقق الواقعي

كل إجراء يحفظ `rule_key` والمقاييس والاستقرار والقيد وخطوة التحقق. الأساليب المناسبة لاحقاً تشمل A/B tests مضبوطة، holdout زمني، مراجعة توافق المنتجات، قياس أثر مسبق التعريف، ومراقبة الآثار الجانبية. لا توجد نتائج مالية مقاسة في المشروع.
"""
        ),
        _markdown("## استعداد Phase 6"),
        _code(
            """
display(Image(filename=str(project_path("outputs", "figures", "business_action_category_distribution.png")), width=900))
print("Prepared for later WEKA execution and Python-versus-WEKA audit. WEKA has not been run.")
"""
        ),
    ]
    return notebook


def write_phase5_notebooks(directory: Path | None = None) -> list[Path]:
    """Write all deterministic Phase 5 notebook sources."""
    notebook_directory = directory or ensure_directory("notebooks")
    targets = {
        notebook_directory / "06_rule_quality_and_stability.ipynb": build_rule_quality_notebook(),
        notebook_directory / "07_interactive_lab.ipynb": build_interactive_notebook(),
        notebook_directory / "09_business_insights.ipynb": build_business_notebook(),
    }
    for path, notebook in targets.items():
        nbf.write(notebook, path)
    return list(targets)


if __name__ == "__main__":
    for notebook_path in write_phase5_notebooks():
        print(notebook_path)
