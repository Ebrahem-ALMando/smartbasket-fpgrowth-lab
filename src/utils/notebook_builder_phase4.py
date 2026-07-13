"""Build the Arabic-first Phase 4 teaching and mining notebooks."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

from src.data.paths import ensure_directory
from src.utils.notebook_builder import KERNEL_METADATA


def _markdown(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text.strip())


def _code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(source.strip())


def build_manual_tree_notebook() -> nbf.NotebookNode:
    """Create Notebook 02 without using mlxtend for the teaching result."""
    notebook = nbf.v4.new_notebook(metadata=KERNEL_METADATA.copy())
    notebook.cells = [
        _markdown(
            """
# 02 — بناء FP-Tree يدوياً خطوة بخطوة

هذا مثال **تعليمي حتمي** من ست معاملات صغيرة، وليس نتيجة من UCI Online Retail. يشرح البنية الداخلية لخوارزمية FP-Growth من المبادئ الأولى، ولا يستدعي `mlxtend` لاستخراج النتيجة اليدوية.
"""
        ),
        _markdown(
            """
## لماذا طُورت FP-Growth؟

تولد Apriori مرشحين مستوى بعد مستوى ثم تمسح البيانات لاختبار دعمهم. عند انخفاض Minimum Support أو اتساع عدد المنتجات قد يكبر فضاء المرشحين بشدة. تضغط FP-Growth المعاملات في **FP-Tree** تشترك فيها البدايات المتشابهة، ثم تستخرج الأنماط من Conditional Pattern Bases من دون توليد المرشحين بالطريقة نفسها.
"""
        ),
        _code(
            """
from pathlib import Path
import sys
import pandas as pd
from IPython.display import FileLink, Image, display

from src.data.paths import PROJECT_ROOT, project_path
from src.mining.fp_tree_educational import FPTree, build_educational_tree
from src.mining.fp_tree_steps import generate_educational_outputs

assert Path.cwd().resolve() == PROJECT_ROOT
assert ".venv" in sys.executable
generation_summary = generate_educational_outputs(minimum_support_count=3)
generation_summary
"""
        ),
        _markdown("## المعاملات التعليمية وحساب التكرار"),
        _code(
            """
transactions = pd.read_csv(project_path("outputs", "tables", "manual_fp_tree_transactions.csv"))
frequencies = pd.read_csv(project_path("outputs", "tables", "manual_fp_tree_item_frequencies.csv"))
display(transactions)
display(frequencies)
"""
        ),
        _markdown(
            """
Minimum Support العددي هو 3 من 6 معاملات. لذلك تبقى Bread وMilk وButter، بينما تُحذف Eggs وCoffee. الترتيب العالمي حتمي: الدعم تنازلياً ثم الاسم أبجدياً لكسر التعادل، أي Bread ثم Milk ثم Butter.
"""
        ),
        _markdown("## إدخال المعاملات وإعادة استخدام Shared Prefix"),
        _code(
            """
for step in sorted(project_path("outputs", "figures", "manual_fp_tree_steps").glob("step_*.png")):
    display(Image(filename=str(step), width=950))
"""
        ),
        _markdown(
            """
العقدة الخضراء أُنشئت في الخطوة الحالية، والصفراء زيد عدادها. عندما تدخل T2 بعد T1 لا يُنشأ مسار Bread→Milk جديد، بل يعاد استخدامه وتزداد العدادات. يحتفظ **Header Table** بالدعم الكلي، وتصل **Node-Link** جميع عقد العنصر نفسه عبر الفروع.
"""
        ),
        _markdown("## Header Table وNode-Link"),
        _code(
            """
header = pd.read_csv(project_path("outputs", "tables", "manual_fp_tree_header_table.csv"))
display(header)
tree, raw_frequencies = build_educational_tree(minimum_support_count=3)
assert [node.count for node in tree.linked_nodes("Butter")] == [2, 1, 1]
"""
        ),
        _markdown("## Conditional Pattern Base وConditional FP-Tree"),
        _code(
            """
conditional_bases = pd.read_csv(project_path("outputs", "tables", "manual_fp_tree_conditional_bases.csv"))
display(conditional_bases)
butter_base = tree.conditional_pattern_base("Butter")
butter_conditional_tree = FPTree.build(butter_base, minimum_support_count=3)
print("Butter conditional base:", butter_base)
print("Conditional frequent supports:", butter_conditional_tree.item_supports)
"""
        ),
        _markdown(
            """
قاعدة Butter الشرطية هي Bread→Milk بوزن 2، وBread بوزن 1، وMilk بوزن 1. داخل السياق الشرطي يصبح دعم Bread=3 ودعم Milk=3. أما Bread+Milk+Butter فدعمه 2 فقط، لذلك لا يمر بالعتبة 3.
"""
        ),
        _markdown("## استخراج Frequent Itemsets والتحقق اليدوي"),
        _code(
            """
itemsets = pd.read_csv(project_path("outputs", "tables", "manual_fp_tree_frequent_itemsets.csv"))
display(itemsets)
expected = {
    "Bread": 5, "Butter": 4, "Milk": 5,
    "Bread | Butter": 3, "Bread | Milk": 4, "Butter | Milk": 3,
}
assert dict(zip(itemsets.itemset_key, itemsets.support_count)) == expected
print("Manual verification passed for all six frequent itemsets.")
"""
        ),
        _markdown("## العارض التفاعلي للخطوات"),
        _code(
            """
viewer = Path("outputs") / "interactive" / "manual_fp_tree_steps.html"
assert project_path(*viewer.parts).exists()
display(FileLink(str(viewer), result_html_prefix="Open the self-contained step viewer: "))
"""
        ),
        _markdown(
            """
## الفصل عن تحليل البيانات الحقيقية

النتيجة أعلاه خاصة بالمثال التعليمي Bread/Milk/Butter. تحليل UCI الحقيقي موجود في Notebook 04 ويستخدم `mlxtend.fpgrowth` على 17,901 معاملة UK. لا تُنسب أرقام المثال الصغير إلى المتجر الحقيقي.
"""
        ),
    ]
    return notebook


def build_fpgrowth_notebook() -> nbf.NotebookNode:
    """Create Notebook 04 around the reusable full-data experiment pipeline."""
    notebook = nbf.v4.new_notebook(metadata=KERNEL_METADATA.copy())
    notebook.cells = [
        _markdown(
            """
# 04 — تحليل FP-Growth على سلال المملكة المتحدة

ينفذ هذا Notebook البحث المحروس عن Minimum Support، ثم FP-Growth وتوليد Association Rules بواسطة وظائف المشروع القابلة لإعادة الاستخدام. كل النتائج أدناه ناتجة من 17,901 معاملة UK، وليست قيماً مكتوبة يدوياً.
"""
        ),
        _code(
            """
from pathlib import Path
import json
import sys
import pandas as pd
from IPython.display import Image, display

from src.data.paths import PROJECT_ROOT, project_path
from src.mining.basket_loader import load_prepared_basket
from src.mining.pipeline import run_fpgrowth_experiment

assert Path.cwd().resolve() == PROJECT_ROOT
assert ".venv" in sys.executable
prepared = load_prepared_basket()
assert prepared.matrix.shape == (17_901, 3_791)
assert set(prepared.matrix.data.tolist()) == {1}
print(f"UK basket: {prepared.transaction_count:,} × {prepared.product_count:,}; nnz={prepared.matrix.nnz:,}")
"""
        ),
        _markdown(
            """
## معنى Support count

Support النسبي يقيس نسبة المعاملات، بينما Support count هو العدد الفعلي. يستخدم المشروع `ceil(support × 17,901)` كحد أدنى محافظ. صُممت التجربة قبل التعدين في `MINING_EXPERIMENT_DESIGN.md`، مع `max_len=3` وحدود ناعمة للوقت والذاكرة وحجم النتائج.
"""
        ),
        _markdown("## تنفيذ البحث المحروس والتجربة النهائية"),
        _code(
            """
experiment = run_fpgrowth_experiment()
experiment
"""
        ),
        _code(
            """
sweep = pd.read_csv(project_path("outputs", "tables", "fpgrowth_threshold_sweep.csv"))
metadata = json.loads(project_path("outputs", "tables", "fpgrowth_run_metadata.json").read_text(encoding="utf-8"))
display(sweep)
display(pd.DataFrame({"parameter": metadata.keys(), "value": [str(v) for v in metadata.values()]}))
"""
        ),
        _markdown(
            """
اختيرت 0.5% لأنها أدنى عتبة ناجحة في الشبكة وبقيت دون الضوابط، مع أنماط ثنائية وثلاثية وقواعد قابلة للإدارة. تعادل 90 معاملة. اختيرت Confidence=0.70 لأنها أعلى قيمة مرشحة أبقت أكثر من 25 قاعدة، ويستخدم Lift≥1.20 للتفسير. القيد `max_len=3` معلن ويعني أن الأنماط الأطول لم تُنقّب.
"""
        ),
        _markdown("## Frequent Itemsets"),
        _code(
            """
lengths = pd.read_csv(project_path("outputs", "tables", "frequent_itemsets_length_summary.csv"))
itemsets = pd.read_csv(project_path("outputs", "tables", "frequent_itemsets_fpgrowth.csv"))
display(lengths)
display(itemsets.head(15))
assert (itemsets.support_count == (itemsets.support * prepared.transaction_count).round().astype(int)).all()
"""
        ),
        _markdown(
            """
## Association Rules ومقاييسها

- **Support:** انتشار الطرفين معاً.
- **Confidence:** احتمال ظهور Consequent داخل معاملات Antecedent.
- **Lift:** يقارن Confidence بخط أساس Consequent؛ القيمة 1 تعني تقريباً الاستقلال.
- **Leverage:** فرق الدعم المشترك عن المتوقع تحت الاستقلال.
- **Conviction:** يقارن فشل القاعدة المتوقع والفعلي، ويحتاج حذراً عند القيم الحدية.

لا يثبت أي مقياس السببية أو الترتيب الزمني داخل الفاتورة.
"""
        ),
        _code(
            """
rules = pd.read_csv(project_path("outputs", "tables", "association_rules_all.csv"))
selected = pd.read_csv(project_path("outputs", "tables", "association_rules_selected.csv"))
metric_summary = pd.read_csv(project_path("outputs", "tables", "rule_metric_summary.csv"))
display(metric_summary)
display(selected.head(12))
print(f"All rules: {len(rules):,}; selected non-redundant rules: {len(selected):,}")
"""
        ),
        _markdown("## لماذا قد تكون Confidence المرتفعة مضللة؟"),
        _code(
            """
high_confidence_lowest_lift = (
    rules.loc[rules.confidence >= metadata["minimum_confidence"]]
    .sort_values(["lift", "support", "rule_key"])
    [["rule_key", "support", "confidence", "lift", "consequent_support"]]
    .head(10)
)
display(high_confidence_lowest_lift)
"""
        ),
        _markdown(
            """
يمكن أن تكون Confidence مرتفعة لأن Consequent شائع أساساً. لذلك لا تختار السياسة القواعد قبل قراءة Lift وSupport count وLeverage، وتبقي التفسير وصفياً وغير سببي.
"""
        ),
        _markdown("## ترتيبات متعددة للقواعد"),
        _code(
            """
for filename in ["top_rules_by_support.csv", "top_rules_by_confidence.csv", "top_rules_by_lift.csv"]:
    print(filename)
    display(pd.read_csv(project_path("outputs", "tables", filename)).head(10))
"""
        ),
        _markdown("## الرسوم الفعلية"),
        _code(
            """
for filename in [
    "minimum_support_vs_frequent_itemsets.png",
    "frequent_itemsets_by_length.png",
    "association_rule_support_vs_confidence.png",
    "association_rule_lift_distribution.png",
]:
    display(Image(filename=str(project_path("outputs", "figures", filename)), width=900))
"""
        ),
        _markdown(
            """
## القيود والاستعداد لـPhase 5

النتائج خاصة بنطاق UK وسياسة التنظيف وMinimum Support=0.5% و`max_len=3`. الارتباط لا يعني السببية، وارتفاع Lift عند دعم قريب من 90 معاملة يحتاج حذراً تجارياً. أصبحت الأنماط والقواعد والجداول جاهزة لمرحلة لاحقة تختبر الاستقرار وتبني أدوات تفاعلية؛ لم ينفذ هنا Bootstrap أو Product Association Network أو Basket Simulator أو WEKA.
"""
        ),
    ]
    return notebook


def build_apriori_notebook() -> nbf.NotebookNode:
    """Create Notebook 05 for correctness-first fair comparison."""
    notebook = nbf.v4.new_notebook(metadata=KERNEL_METADATA.copy())
    notebook.cells = [
        _markdown(
            """
# 05 — مقارنة FP-Growth وApriori

تقارن هذه الدفترية الصحة قبل السرعة. تستخدم الخوارزميتان مصفوفة UK نفسها، وMinimum Support=0.5%، و`max_len=3`، وترتيب الأعمدة والمعالجة والبيئة نفسها.
"""
        ),
        _code(
            """
from pathlib import Path
import json
import sys
import pandas as pd
from IPython.display import Image, display

from src.data.paths import PROJECT_ROOT, project_path
from src.mining.basket_loader import load_prepared_basket
from src.mining.pipeline import run_comparison_experiment

assert Path.cwd().resolve() == PROJECT_ROOT
assert ".venv" in sys.executable
prepared = load_prepared_basket()
print(prepared.matrix.shape, prepared.matrix.nnz)
"""
        ),
        _markdown(
            """
## منهج المقارنة

ينفذ Warm-up واحداً ثم ثلاث تشغيلات مقاسة لكل خوارزمية على البيانات الكاملة، ويعرض median wall-clock time. قياس الذاكرة هو RSS قبل/بعد فقط وليس Peak Memory. يستخدم Apriori وضع `low_memory=True` لحماية الموارد من دون تغيير Support أو `max_len`.
"""
        ),
        _code(
            """
comparison_result = run_comparison_experiment()
comparison_result
"""
        ),
        _markdown("## تكافؤ Frequent Itemsets"),
        _code(
            """
equivalence = json.loads(project_path("outputs", "comparisons", "itemset_equivalence_summary.json").read_text(encoding="utf-8"))
display(pd.DataFrame([equivalence]))
assert equivalence["equivalent"]
assert equivalence["fpgrowth_only_itemsets"] == 0
assert equivalence["apriori_only_itemsets"] == 0
"""
        ),
        _markdown(
            """
تُطابق Itemsets بمفتاح canonical مرتب، وتقارن قيم Support بتسامح مطلق `1e-12`. لا تصبح مقارنة الوقت ذات معنى قبل نجاح هذا الفحص.
"""
        ),
        _markdown("## Runtime والذاكرة التقريبية"),
        _code(
            """
benchmark = pd.read_csv(project_path("outputs", "comparisons", "fpgrowth_apriori_benchmark.csv"))
measured = benchmark.loc[benchmark.run_type.eq("measured")]
display(benchmark)
display(measured.groupby("algorithm").agg(
    measured_runs=("runtime_seconds", "size"),
    median_runtime_seconds=("runtime_seconds", "median"),
    median_approximate_rss_delta_bytes=("approximate_rss_delta_bytes", "median"),
))
"""
        ),
        _markdown(
            """
لا تمثل RSS delta قمة الذاكرة، وقد تكون سالبة بسبب تحرير الذاكرة وGarbage Collection. لذلك لا تُستخدم لإعلان تفوق ذاكرة قطعي.
"""
        ),
        _markdown("## Scalability على كسور حتمية متطابقة"),
        _code(
            """
scalability = pd.read_csv(project_path("outputs", "comparisons", "scalability_experiment.csv"))
display(scalability[["algorithm", "transaction_fraction", "transaction_count", "minimum_support_count", "frequent_itemset_count", "runtime_seconds"]])
"""
        ),
        _markdown(
            """
تستخدم كل نقطة مقدمة حتمية من ترتيب معاملات Phase 3 نفسه للخوارزميتين. الزمن ليس ملزماً بالزيادة مع عدد الصفوف: عند 25% يصبح Support count صغيراً، وقد تظهر أنماط كثيرة خاصة بتلك الفترة. هذا يوضح أن تكلفة التعدين تتأثر بعدد الأنماط وتركيب البيانات، لا بعدد المعاملات وحده.
"""
        ),
        _markdown("## رسوم المقارنة"),
        _code(
            """
for filename in [
    "fpgrowth_vs_apriori_runtime.png",
    "scalability_fpgrowth_vs_apriori.png",
    "itemset_equivalence_summary.png",
]:
    display(Image(filename=str(project_path("outputs", "figures", filename)), width=900))
"""
        ),
        _markdown(
            """
## التفسير والقيود

النتيجة تقيس هذا dataset وهذا التطبيق والإصدارات والجهاز والإعدادات فقط، ولا تثبت تفوقاً عاماً. `max_len=3` يمنع مقارنة الأنماط الأطول، وscalability تستخدم time-ordered prefixes لا عينات ممثلة. أصبحت شروط المقارنة موثقة لتجربة WEKA لاحقاً، لكن WEKA لم يُنفذ في Phase 4، كما لم تبدأ أدوات Phase 5 التفاعلية أو Bootstrap.
"""
        ),
    ]
    return notebook


def write_phase4_notebooks(directory: Path | None = None) -> list[Path]:
    """Write deterministic source notebooks for Phase 4."""
    notebook_directory = directory or ensure_directory("notebooks")
    targets = {
        notebook_directory / "02_manual_fp_tree_example.ipynb": build_manual_tree_notebook(),
        notebook_directory / "04_fpgrowth_analysis.ipynb": build_fpgrowth_notebook(),
        notebook_directory / "05_apriori_comparison.ipynb": build_apriori_notebook(),
    }
    for path, notebook in targets.items():
        nbf.write(notebook, path)
    return list(targets)


if __name__ == "__main__":
    for notebook_path in write_phase4_notebooks():
        print(notebook_path)
