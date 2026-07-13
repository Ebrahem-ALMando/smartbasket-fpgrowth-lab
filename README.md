# SmartBasket FP-Growth Lab

## Academic Titles

**العنوان العربي:** استخراج أنماط الشراء وقواعد الارتباط باستخدام خوارزمية FP-Growth: تطبيق عملي ومقارنة بين Python وWEKA

**English title:** Market Basket Analysis Using FP-Growth: A Practical Comparison Between Python and WEKA

## Overview

مشروع جامعي لمقرر تنقيب البيانات (Data Mining) يهدف إلى بناء مختبر قابل لإعادة الإنتاج لتحليل سلة المشتريات (Market Basket Analysis). يشرح المشروع تعدين قواعد الارتباط (Association Rule Mining) وبنية شجرة FP-Tree، ثم يخطط لتطبيق FP-Growth على بيانات معاملات حقيقية ومقارنة النتائج مع Apriori ومع أداة WEKA. اكتملت مرحلة اقتناء البيانات وتدقيقها وتجهيز سلال المعاملات، ولم يبدأ تعدين الأنماط بعد.

## Main Objective

فهم كيفية اكتشاف مجموعات المنتجات المتكررة وقواعد الارتباط وتقييمها وتفسيرها، مع تحويل الأنماط الموثوقة لاحقاً إلى توصيات أعمال واضحة من دون الاكتفاء باستدعاء مكتبة جاهزة.

## Planned Features

- شرح نظري وتطبيقي لمقاييس Support وConfidence وLift.
- بناء تعليمي متدرج لشجرة FP-Tree.
- تطبيق FP-Growth ومقارنته بخوارزمية Apriori.
- مستكشف تفاعلي لعتبات القواعد ومحاكي توصية قائم على القواعد.
- شبكة ارتباط المنتجات وكاشف القواعد المضللة.
- تحليل استقرار القواعد باستخدام Bootstrap resampling.
- تدقيق منظم للنتائج بين Python وWEKA.
- تحويل القواعد القوية إلى مقترحات أعمال قابلة للفهم.

## Repository Structure

```text
data/           Raw, interim, and processed datasets
notebooks/      Focused Jupyter notebooks planned for later phases
src/            Reusable data, mining, evaluation, visualization, and recommendation logic
outputs/        Generated figures, interactive exports, tables, and comparisons
weka/           WEKA-compatible datasets, results, and screenshots
docs/           References and project notes
report/         Final report assets planned for a later phase
tests/          Automated tests planned with the implementation
```

## Current Status

**Phase 3 Complete — Official Data Audited and Transaction Baskets Prepared**

نُزلت مجموعة UCI Online Retail من المصدر الرسمي، وسُجل الترخيص والمصدر وبصمة SHA-256. اكتمل تدقيق 541,909 سطراً وخط التنظيف القابل لإعادة التشغيل وإعادة بناء المعاملات، وحُفظت مصفوفة السلة الثنائية بصيغة sparse. نُفذ الدفتران `01_project_introduction.ipynb` و`03_data_preparation.ipynb` من clean kernels بنجاح. لم تُنفذ FP-Growth أو Apriori، ولم تُولد قواعد ارتباط أو نتائج WEKA.

## Environment Setup

توجد البيئة المعتمدة في `.venv` وتستخدم Python 3.11.9. يحتفظ `requirements.txt` بنطاقات الاعتماديات المقصودة، بينما يسجل `requirements-resolved.txt` الإصدارات الدقيقة التي اجتازت التحقق. توجد الأوامر المختبرة وتعليمات اختيار المفسر في `docs/notes/ENVIRONMENT_SETUP.md`.

## Reproducibility Principles

- إبقاء البيانات الخام دون تعديل وحفظ كل مرحلة معالجة في موقع مستقل.
- استخدام مسارات نسبية وتسجيل إصدارات الحزم ومعاملات التجارب.
- تثبيت بذرة عشوائية موحدة عند وجود عمليات عشوائية.
- تشغيل الدفاتر من البداية إلى النهاية من دون الاعتماد على حالة مخفية.
- توليد القيم والجداول آلياً وعدم تعديل النتائج يدوياً.

## WEKA Comparison Goal

ستُصدّر البيانات المعالجة نفسها إلى تنسيق متوافق مع WEKA، ثم تُضبط عتبات FP-Growth قدر الإمكان لتدقيق القواعد المنطقية ومقاييسها وترتيبها وأسباب أي اختلاف عن Python. لن تُعامل لقطات الشاشة على أنها الدليل الوحيد للمقارنة.

## Data and Results Notice

المصدر المعتمد هو UCI Online Retail بترخيص CC BY 4.0. توجد معلومات المصدر والنزاهة في `docs/references/ONLINE_RETAIL_SOURCE.md`، والخصائص المرصودة والقيود في `docs/references/ONLINE_RETAIL_DATASET_CARD.md`. الإحصاءات الحالية تخص جودة البيانات وتجهيزها فقط؛ لا توجد بعد نتائج تعدين أو قواعد ارتباط.
