"""Build the two Phase 3 notebooks with deterministic metadata and cell order."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

from src.data.paths import ensure_directory


KERNEL_METADATA = {
    "kernelspec": {
        "display_name": "Python 3 (.venv)",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "version": "3.11.9"},
}


def _markdown(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text.strip())


def _code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(source.strip())


def build_introduction_notebook() -> nbf.NotebookNode:
    """Create the Arabic-first conceptual project introduction notebook."""
    notebook = nbf.v4.new_notebook(metadata=KERNEL_METADATA.copy())
    notebook.cells = [
        _markdown(
            """
# SmartBasket FP-Growth Lab

## استخراج أنماط الشراء وقواعد الارتباط باستخدام FP-Growth

**English title:** Market Basket Analysis Using FP-Growth: A Practical Comparison Between Python and WEKA

هذا Notebook مقدمة أكاديمية للمشروع ولمفاهيم **تعدين قواعد الارتباط (Association Rule Mining)**. لا يحتوي على تنفيذ FP-Growth أو Apriori، ولا توجد في هذه المرحلة نتائج قواعد ارتباط.
"""
        ),
        _markdown(
            """
## مشكلة الأعمال وسياق تنقيب البيانات

تحتوي متاجر التجزئة على عدد كبير من الفواتير، وكل فاتورة تضم منتجات قد تظهر معاً بصورة متكررة. يصعب اكتشاف هذه العلاقات يدوياً، كما أن التكرار وحده لا يثبت أن العلاقة مفيدة. يهدف **تنقيب البيانات (Data Mining)** هنا إلى تحويل سجلات الشراء إلى أنماط قابلة للقياس، ثم تفسيرها بحذر لدعم أفكار مثل البيع المتقاطع والحزم وترتيب المنتجات.

العلاقة المكتشفة لا تعني السببية. شراء منتجين معاً قد يتأثر بالموسم أو شعبية أحدهما أو تصميم المتجر أو خصم مؤقت.
"""
        ),
        _markdown(
            """
## المصطلحات الأساسية

| المصطلح | المعنى في المشروع |
|---|---|
| المعاملة (Transaction) | فاتورة أو سلة شراء واحدة ذات معرّف واضح. |
| العنصر (Item) | منتج واحد يمكن أن يظهر داخل السلة. |
| مجموعة العناصر (Itemset) | مجموعة منتجات يُدرس ظهورها المشترك من دون اعتبار ترتيبها. |
| مجموعة العناصر المتكررة (Frequent Itemset) | Itemset تتجاوز عتبة الدعم الأدنى المحددة. |
| قاعدة الارتباط (Association Rule) | علاقة على صورة `X → Y` تصف تكرار ظهور `Y` عندما تظهر `X`. |

في القاعدة `X → Y` تسمى `X` **المقدمة (Antecedent)** وتسمى `Y` **النتيجة (Consequent)**.
"""
        ),
        _markdown(
            """
## مثال تعليمي صغير — ليس من بيانات المشروع

المثال التالي مصمم لشرح المصطلحات فقط ولا يمثل نتيجة من UCI Online Retail:

| السلة التعليمية | العناصر |
|---|---|
| T1 | خبز، حليب |
| T2 | خبز، شاي |
| T3 | خبز، حليب، شاي |
| T4 | حليب |

يمكن دراسة Itemset مثل `{خبز، حليب}` أو قاعدة مثل `{خبز} → {حليب}`. الأعداد الناتجة من هذا الجدول تعليمية ولا تُعرض بوصفها دليلاً تجارياً.
"""
        ),
        _markdown(
            """
## Support وConfidence وLift

- **الدعم (Support):** نسبة جميع المعاملات التي تحتوي النمط. دعم `{X,Y}` يجيب: ما مدى انتشار ظهورهما معاً؟
- **الثقة (Confidence):** نسبة المعاملات التي تحتوي `X` وتحتوي أيضاً `Y`. تجيب: عندما يظهر `X`، كم مرة يظهر `Y`؟
- **الرفع (Lift):** يقارن ظهور `X` و`Y` معاً بما نتوقعه لو كانا مستقلين. قيمة أكبر من 1 تشير إلى ارتباط إيجابي، والقيمة القريبة من 1 تشير إلى أن القاعدة لا تضيف كثيراً فوق شيوع `Y`، والقيمة الأقل من 1 تشير إلى ارتباط سلبي.

لا يكفي عرض الصيغة؛ يجب تفسير المقام والسياق وحجم التغطية. القاعدة ذات Support شديد الانخفاض قد تكون هشة حتى إن كان Lift مرتفعاً.
"""
        ),
        _markdown(
            """
## لماذا قد تكون Confidence مضللة؟

إذا كان المنتج `Y` موجوداً في معظم السلال، فقد تكون Confidence للقاعدة `X → Y` مرتفعة مهما كان `X`. عندها يكشف Lift القريب من 1 أن معرفة `X` لم تحسن التوقع كثيراً مقارنة بالمعدل الأساسي لـ `Y`. لذلك سيقيّم المشروع القواعد لاحقاً باستخدام Support وConfidence وLift ومقاييس مساندة، لا Confidence منفردة.
"""
        ),
        _markdown(
            """
## Apriori وFP-Growth على مستوى عالٍ

| الجانب | Apriori | FP-Growth |
|---|---|---|
| الفكرة | يولد مجموعات مرشحة مستوى بعد مستوى ويختبر دعمها. | يضغط المعاملات في FP-Tree وينقّب أنماطاً شرطية. |
| المرشحون | قد يكون عددهم كبيراً عند انخفاض الدعم. | لا يعتمد على توليد المرشحين بالطريقة نفسها. |
| الاستخدام في المشروع | خوارزمية مقارنة للتحقق من تطابق Frequent Itemsets والأداء. | الخوارزمية الرئيسة مع شرح داخلي لبنية الشجرة. |

لن يفترض المشروع أن FP-Growth أسرع دائماً؛ ستُقارن الخوارزميتان لاحقاً على البيانات والإعدادات والجهاز نفسها.
"""
        ),
        _markdown(
            """
## المقارنة المخططة بين Python وWEKA

ستُستخدم سلال معالجة من المصدر نفسه وبمجال منتجات وعتبات متطابقة قدر الإمكان. ستُقارن القواعد المنطقية بعد توحيد الترتيب والتقريب، مع تسجيل معاملات WEKA وتفسير اختلاف تعريف المقاييس أو preprocessing. لن تكون لقطة الشاشة الدليل الوحيد.
"""
        ),
        _markdown(
            """
## الميزات الإبداعية المخططة

- باني FP-Tree خطوة بخطوة.
- مستكشف عتبات Minimum Support وMinimum Confidence وMinimum Lift.
- محاكي توصية سلة قائم على القواعد، وليس توصية شخصية.
- شبكة ارتباط المنتجات.
- كاشف القواعد المضللة والمتكررة.
- Rule Stability Analysis باستخدام Bootstrap.
- مولد إجراءات أعمال مشروطة بجودة الدليل.
- جدول تدقيق Python versus WEKA.
"""
        ),
        _markdown(
            """
## المرحلة الحالية ومصدر البيانات

اعتمد المشروع مجموعة **UCI Online Retail** من UCI Machine Learning Repository، DOI: [10.24432/C5BW33](https://doi.org/10.24432/C5BW33)، بترخيص CC BY 4.0. تنفذ Phase 3 التحقق والتنظيف وإعادة بناء السلال فقط.

**لا توجد حتى الآن Frequent Itemsets أو Association Rules أو نتائج FP-Growth أو Apriori أو WEKA.** ستنتج أي نتائج تعدين في مرحلة لاحقة بواسطة كود قابل لإعادة التشغيل.
"""
        ),
    ]
    return notebook


def build_preparation_notebook() -> nbf.NotebookNode:
    """Create the executable Phase 3 data-preparation notebook."""
    notebook = nbf.v4.new_notebook(metadata=KERNEL_METADATA.copy())
    notebook.cells = [
        _markdown(
            """
# 03 — تجهيز بيانات Online Retail

يوثق هذا Notebook مصدر البيانات، التدقيق، سياسة التنظيف، إعادة بناء المعاملات، اختيار النطاق، والتخزين المتناثر. يستدعي المنطق القابل لإعادة الاستخدام من `src/data` ولا يطبق FP-Growth أو Apriori ولا يولد قواعد ارتباط.
"""
        ),
        _markdown("## 1. التحقق من البيئة والمسارات"),
        _code(
            """
from pathlib import Path
import json
import sys

import pandas as pd
from IPython.display import Image, display
from scipy import sparse

from src.data.paths import PROJECT_ROOT, project_path
from src.data.pipeline import run_pipeline
from src.data.raw_loader import verify_workbook_integrity

assert Path.cwd().resolve() == PROJECT_ROOT
assert ".venv" in sys.executable
print(f"Python executable: {sys.executable}")
print(f"Project root: {PROJECT_ROOT}")
print(f"Raw checksum: {verify_workbook_integrity()}")
"""
        ),
        _markdown("## 2. أصل البيانات (Provenance)"),
        _code(
            """
metadata = json.loads(
    project_path("data", "raw", "online_retail", "source_metadata.json").read_text(encoding="utf-8")
)
pd.DataFrame(
    {
        "field": ["dataset_name", "publisher", "contributor", "license", "retrieval_date", "official_doi"],
        "value": [metadata[key] for key in ["dataset_name", "publisher", "contributor", "license", "retrieval_date", "official_doi"]],
    }
)
"""
        ),
        _markdown(
            """
## 3. تنفيذ خط التجهيز القابل لإعادة الإنتاج

تعيد الدالة التالية التحقق من checksum، وتقرأ workbook، وتولد تدقيق raw، وتطبق السياسة، وتفصل accepted/rejected، وتعيد بناء المعاملات، وتقارن النطاقات، وتحفظ CSR matrix والرسوم. لا يوجد منطق تعدين داخلها.
"""
        ),
        _code(
            """
pipeline_summary = run_pipeline()
pipeline_summary
"""
        ),
        _markdown("## 4. المخطط الخام ومشكلات الجودة"),
        _code(
            """
raw_schema = pd.read_csv(project_path("outputs", "tables", "raw_schema.csv"))
raw_missing = pd.read_csv(project_path("outputs", "tables", "raw_missing_values.csv"))
raw_quality = pd.read_csv(project_path("outputs", "tables", "raw_quality_summary.csv"))
display(raw_schema)
display(raw_missing)
display(raw_quality)
"""
        ),
        _markdown(
            """
## 5. سياسة التنظيف

توجد السياسة الكاملة في `docs/notes/DATA_CLEANING_POLICY.md`. أهم مبادئها: raw immutable، الإلغاء بحسب `InvoiceNo` الذي يبدأ بـ `C`، فصل الكمية والسعر غير الموجبين، عدم تخمين الوصف، قبول غياب `CustomerID` لتحليل السلة، تصنيف الخدمات بأكواد مرصودة فقط، وتدقيق النسخ الكاملة الزائدة.
"""
        ),
        _markdown("## 6. Data Lineage والسجلات المفصولة"),
        _code(
            """
lineage = pd.read_csv(project_path("outputs", "tables", "data_cleaning_lineage.csv"))
rejections = pd.read_csv(project_path("outputs", "tables", "cleaning_rejection_reasons.csv"))
assert lineage.iloc[-1]["output_record_count"] == pipeline_summary.valid_line_items
assert lineage["removed_or_separated_count"].sum() == pipeline_summary.rejected_records
display(lineage)
display(rejections)
"""
        ),
        _markdown("## 7. إعادة بناء المعاملات وإحصاءات حجم السلة"),
        _code(
            """
processed_summary = pd.read_csv(project_path("outputs", "tables", "processed_dataset_summary.csv"))
basket_sizes = pd.read_csv(project_path("outputs", "tables", "transaction_size_summary.csv"))
display(processed_summary)
display(basket_sizes)
"""
        ),
        _markdown("## 8. مقارنة البلدان واختيار Core Scope"),
        _code(
            """
country_summary = pd.read_csv(project_path("outputs", "tables", "country_summary.csv"))
scope_table = pd.read_csv(project_path("outputs", "tables", "scope_comparison.csv"))
display(scope_table)
display(country_summary.head(10))
selected = scope_table.loc[scope_table["scope"].eq(pipeline_summary.core_scope)].iloc[0]
print(
    f"Selected scope: {selected['scope']} — "
    f"{int(selected['transaction_count']):,} transactions, "
    f"{selected['transaction_share_percentage']:.2f}% of valid transactions."
)
"""
        ),
        _markdown(
            """
اختيرت المملكة المتحدة لأنها السوق المهيمنة وتحتفظ بأكثر من 90% من المعاملات الصالحة، مع سياق سوق أكثر اتساقاً وعرض مصفوفة قريب من النطاق الكامل. بقي جدول جميع البلدان محفوظاً للمقارنة ولم يُحذف.
"""
        ),
        _markdown("## 9. Basket Matrix والتخزين المتناثر"),
        _code(
            """
matrix = sparse.load_npz(project_path("data", "processed", "online_retail_basket_matrix.npz"))
column_metadata = json.loads(
    project_path("data", "processed", "online_retail_basket_columns.json").read_text(encoding="utf-8")
)
assert matrix.shape == tuple(column_metadata["shape"])
assert set(matrix.data.tolist()) <= {1}
print(f"CSR shape: {matrix.shape}")
print(f"Nonzero entries: {matrix.nnz:,}")
print(f"Density: {matrix.nnz / (matrix.shape[0] * matrix.shape[1]):.6%}")
print("The matrix is binary and stored as compressed SciPy CSR data.")
"""
        ),
        _markdown("## 10. رسوم استكشافية مختارة"),
        _code(
            """
for figure_name in [
    "raw_missing_value_profile.png",
    "cleaning_impact_by_rejection_reason.png",
    "top_products_by_transaction_frequency.png",
]:
    display(Image(filename=str(project_path("outputs", "figures", figure_name)), width=900))
"""
        ),
        _markdown(
            """
## 11. الجاهزية للمرحلة التالية

أصبحت البيانات الخام موثقة ببصمة، والسجلات المقبولة والمرفوضة منفصلة، والمعاملات معاد بناؤها، ومصفوفة السلة الثنائية محفوظة بصيغة sparse مع خرائط صفوف وأعمدة مستقرة. هذه النتائج تصف **جودة البيانات وتجهيزها فقط**.

**لم يُنفذ FP-Growth أو Apriori، ولم تُولد Frequent Itemsets أو Association Rules، ولم يُجر تحليل WEKA.**
"""
        ),
    ]
    return notebook


def write_phase3_notebooks(directory: Path | None = None) -> list[Path]:
    """Write deterministic source notebooks and return their paths."""
    notebook_directory = directory or ensure_directory("notebooks")
    targets = {
        notebook_directory / "01_project_introduction.ipynb": build_introduction_notebook(),
        notebook_directory / "03_data_preparation.ipynb": build_preparation_notebook(),
    }
    for path, notebook in targets.items():
        nbf.write(notebook, path)
    return list(targets)


if __name__ == "__main__":
    for notebook_path in write_phase3_notebooks():
        print(notebook_path)
