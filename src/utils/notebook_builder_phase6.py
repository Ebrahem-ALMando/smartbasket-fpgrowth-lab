"""Build the Arabic-first WEKA comparison notebook from saved evidence."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

from src.data.paths import ensure_directory
from src.utils.notebook_builder import KERNEL_METADATA


def _markdown(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text.strip())


def _code(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(source.strip())


def build_weka_comparison_notebook() -> nbf.NotebookNode:
    """Create Notebook 08 without embedding large rule tables."""
    notebook = nbf.v4.new_notebook(metadata=KERNEL_METADATA.copy())
    notebook.cells = [
        _markdown(
            """
# 08 — مقارنة FP-Growth بين Python وWEKA

تُستخدم WEKA هنا كتطبيق مستقل لتدقيق القواعد، لا لإثبات أن شكل المخرجات أو ترتيبها يجب أن يتطابق. الدليل الأساسي هو sparse ARFF متحقق منه، Java AssociationRules API، canonical rule keys، وaudit آلي. لا تكفي screenshots وحدها.
"""
        ),
        _code(
            """
from pathlib import Path
import json, sys
import pandas as pd
from IPython.display import Image, FileLink, display

from src.data.paths import PROJECT_ROOT, project_path

assert Path.cwd().resolve() == PROJECT_ROOT
assert ".venv" in sys.executable
environment = json.loads(project_path("weka", "results", "weka_environment.json").read_text(encoding="utf-8"))
run = json.loads(project_path("weka", "results", "weka_run_metadata.json").read_text(encoding="utf-8"))
display(pd.DataFrame([environment]))
display(pd.DataFrame([{k: run[k] for k in ["status", "instances", "attributes", "presence_count", "rule_count", "loading_seconds", "mining_seconds", "bridge_total_seconds"]}]))
"""
        ),
        _markdown(
            """
## البيئة ومنهج التنفيذ

استُخدمت WEKA 3.8.7 stable الرسمية وBellSoft OpenJDK 25.0.2 amd64 من التوزيعة نفسها. جُمّع bridge بمترجم BellSoft JDK مطابق لأن runtime المرفقة لا تتضمن `javac`. استخرج bridge القواعد من `AssociationRules API` وحفظ console text مستقلاً. شُغلت class الرسمية CLI كدليل ثانوي.
"""
        ),
        _markdown("## تصميم sparse ARFF وInput equivalence"),
        _code(
            """
arff = json.loads(project_path("weka", "datasets", "arff_export_metadata.json").read_text(encoding="utf-8"))
input_check = json.loads(project_path("outputs", "comparisons", "python_weka_input_equivalence_summary.json").read_text(encoding="utf-8"))
display(pd.DataFrame([arff]))
display(pd.DataFrame([input_check]))
assert input_check["passed"]
assert (input_check["instance_count"], input_check["attribute_count"], input_check["presence_count"]) == (17901, 3791, 473636)
"""
        ),
        _markdown(
            """
كل منتج nominal attribute بالقيم `{0,1}`؛ omitted sparse value يعني غياب المنتج والقيمة الصريحة 1 تعني حضوره. alias من الشكل `P_000000` يعتمد رقم العمود، ثم يعاد إلى StockCode بواسطة mapping. بقي ترتيب transactions والمنتجات مطابقاً للـCSR الأصلي وفق checksums وعينات حتمية وفحص كامل للـpresence count.
"""
        ),
        _markdown("## محاذاة معاملات Python وWEKA"),
        _code(
            """
alignment = pd.read_csv(project_path("outputs", "comparisons", "python_weka_parameter_alignment.csv"))
display(alignment)
"""
        ),
        _markdown(
            """
التجربة الأساسية تستخدم Support≥0.005/count≥90، Confidence≥0.70، وmaximum total items=3، دون Lift/stability filters. في WEKA يلزم `-M 0.005` و`-U 1.0`: أثبت diagnostic أن مساواة upper بالـlower تفرض سقف support وتعيد 137 قاعدة فقط. يفعّل `-S` كل القواعد ويعطل top-N search؛ لذا لا يفرض `-N` cutoff.
"""
        ),
        _markdown("## Rule counts وRule overlap"),
        _code(
            """
audit_summary = json.loads(project_path("outputs", "comparisons", "python_weka_rule_audit_summary.json").read_text(encoding="utf-8"))
audit = pd.read_csv(project_path("outputs", "comparisons", "python_weka_rule_audit.csv"))
display(pd.DataFrame([audit_summary]))
display(audit[["rule_key", "presence_status", "overall_metric_status", "python_source_rank", "weka_source_rank"]].head(12))
assert audit_summary["python_rule_count"] == audit_summary["weka_rule_count"] == audit_summary["common_rules"] == 3468
"""
        ),
        _markdown(
            """
تتطابق هوية كل القواعد: لا Python-only ولا WEKA-only ولا duplicate أو mapping failure. لكن الترتيب لا يتطابق لأن Python يرتب حسب Support أولاً بينما WEKA يعرض حسب primary metric Confidence؛ يُدقق الترتيب منفصلاً عن الهوية.
"""
        ),
        _markdown("## فروق المقاييس: exact وضمن tolerance"),
        _code(
            """
differences = pd.read_csv(project_path("outputs", "comparisons", "python_weka_metric_differences.csv"))
metric_counts = differences.groupby(["metric", "match_status"]).size().unstack(fill_value=0)
metric_maxima = differences.groupby("metric").agg(max_absolute=("absolute_difference", "max"), max_relative=("relative_difference", "max"))
display(metric_counts)
display(metric_maxima)
exact_examples = audit.loc[(audit.presence_status == "common") & (audit.leverage_match_status == "exact"), ["rule_key", "python_leverage", "weka_leverage"]].head(5)
tolerance_examples = audit.loc[audit.lift_match_status == "tolerance", ["rule_key", "python_lift", "weka_lift", "lift_absolute_difference"]].head(5)
display(exact_examples)
display(tolerance_examples)
"""
        ),
        _markdown("## فرق تعريف Conviction"),
        _code(
            """
formula = json.loads(project_path("outputs", "comparisons", "python_weka_conviction_formula_evidence.json").read_text(encoding="utf-8"))
display(pd.DataFrame([formula]))
display(audit.nlargest(6, "conviction_absolute_difference")[["rule_key", "python_conviction", "weka_conviction", "conviction_absolute_difference"]])
"""
        ),
        _markdown(
            """
هذا ليس rounding: source الفعلي لـWEKA يقسم على `(premise_count − joint_count + 1)`، بينما mlxtend يستخدم المقام غير الملساء بلا `+1`. لذلك تختلف Conviction لكل 3,468 قاعدة رغم توافق Support/Confidence/Lift/Leverage. تحفظ القيم الأصلية؛ لا نستبدل WEKA metric بقيمة مشتقة لإخفاء الفرق.
"""
        ),
        _markdown("## Runtime comparison"),
        _code(
            """
runtime_runs = pd.read_csv(project_path("outputs", "comparisons", "python_weka_runtime_comparison.csv"))
runtime_summary = pd.read_csv(project_path("outputs", "comparisons", "python_weka_runtime_summary.csv"))
display(runtime_runs)
display(runtime_summary)
"""
        ),
        _markdown(
            """
نفذت warm-up وثلاث measured runs. يشمل mining استخراج itemsets والقواعد في التطبيقين؛ WEKA loading وJVM startup مسجلان منفصلين. هذه نتيجة هذا الجهاز وهذه representations فقط: CSR/pandas sparse يختلف عن ARFF/Java objects، وJIT/GC/process startup وقياس الذاكرة التقريبي تمنع ادعاء تفوق عام.
"""
        ),
        _markdown("## Figures الفعلية"),
        _code(
            """
for filename in [
    "python_weka_rule_overlap_summary.png",
    "python_weka_lift_difference_distribution.png",
    "python_weka_maximum_metric_differences.png",
    "python_weka_mining_runtime.png",
    "python_weka_rule_order_difference.png",
    "python_weka_parameter_alignment_summary.png",
]:
    display(Image(filename=str(project_path("outputs", "figures", filename)), width=850))
"""
        ),
        _markdown("## WEKA Explorer للعرض الصفي"),
        _code(
            """
display(FileLink("docs/notes/WEKA_EXPLORER_GUIDE.md"))
display(FileLink("weka/run_weka_gui.ps1"))
print("Screenshots are a manual presentation task; no screenshots were fabricated.")
"""
        ),
        _markdown(
            """
## الخلاصة والقيود

في هذه التجربة تتطابق القواعد المنطقية وsupport counts بالكامل، وتتوافق Support/Confidence/Lift ضمن دقة floating-point وتطابق Leverage تماماً. تختلف Conviction بسبب تعريف WEKA الملساء، ويختلف ترتيب العرض. runtime تجريبي محلي وليس حكماً عاماً. GUI screenshots مؤجلة يدوياً. لم يبدأ التقرير HTML/PDF النهائي أو Phase 7.
"""
        ),
    ]
    return notebook


def write_phase6_notebook(directory: Path | None = None) -> Path:
    """Write deterministic Notebook 08 source."""
    notebook_directory = directory or ensure_directory("notebooks")
    target = notebook_directory / "08_weka_comparison.ipynb"
    nbf.write(build_weka_comparison_notebook(), target)
    return target


if __name__ == "__main__":
    print(write_phase6_notebook())

