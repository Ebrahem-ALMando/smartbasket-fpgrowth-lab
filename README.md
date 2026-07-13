# SmartBasket FP-Growth Lab

## Academic Titles

**العنوان العربي:** استخراج أنماط الشراء وقواعد الارتباط باستخدام خوارزمية FP-Growth: تطبيق عملي ومقارنة بين Python وWEKA

**English title:** Market Basket Analysis Using FP-Growth: A Practical Comparison Between Python and WEKA

## Overview

مشروع جامعي لمقرر تنقيب البيانات (Data Mining) يهدف إلى بناء مختبر قابل لإعادة الإنتاج لتحليل سلة المشتريات (Market Basket Analysis). يشرح المشروع FP-Tree ويطبق FP-Growth ويقارنه مع Apriori، ثم يدقق استقرار القواعد وجودتها ويقدم أدوات تفاعلية وتفسيرات أعمال حذرة. تبقى مقارنة WEKA والتقرير النهائي للمراحل اللاحقة.

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

**Phase 6 Complete — Official WEKA Execution and Python–WEKA Audit Ready**

اكتمل Bootstrap rule-stability وأدوات Phase 5، ثم جُهزت WEKA 3.8.7 الرسمية محلياً وصُدرت السلة البريطانية نفسها إلى sparse ARFF وتحقق WEKA من أبعادها وقيم الحضور. نُفذ FPGrowth عبر Java API bridge والـCLI الرسمي، واكتمل تدقيق 3,468 قاعدة core-aligned: تطابقت هوية القواعد بالكامل، وتوافقت Support وConfidence وLift ضمن دقة عددية وتطابقت Leverage، بينما اختلفت Conviction بسبب صيغة WEKA الملساء الموثقة. نُفذ Notebook 08 من clean kernel. بقي التقاط screenshots للـExplorer خطوة عرض يدوية، ولم يبدأ التقرير HTML/PDF النهائي أو Phase 7.

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

المصدر المعتمد هو UCI Online Retail بترخيص CC BY 4.0. توجد تفاصيل Phase 5 في `docs/notes/PHASE_5_DECISION_LOG.md` ومنهج الاستقرار والمختبر والتفسير في الوثائق المرافقة. نتائج القواعد والأدوات وصفية وغير سببية، والإجراءات business candidates غير متحقق منها تجارياً.
