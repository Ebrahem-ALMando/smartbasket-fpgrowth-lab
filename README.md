# SmartBasket FP-Growth Lab

## Academic Titles

**العنوان العربي:** استخراج أنماط الشراء وقواعد الارتباط باستخدام خوارزمية FP-Growth: تطبيق عملي ومقارنة بين Python وWEKA

**English title:** Market Basket Analysis Using FP-Growth: A Practical Comparison Between Python and WEKA

## Overview

مشروع جامعي لمقرر تنقيب البيانات (Data Mining) يهدف إلى بناء مختبر قابل لإعادة الإنتاج لتحليل سلة المشتريات (Market Basket Analysis). يشرح المشروع تعدين قواعد الارتباط (Association Rule Mining) وبنية شجرة FP-Tree، ثم يخطط لتطبيق FP-Growth على بيانات معاملات حقيقية ومقارنة النتائج مع Apriori ومع أداة WEKA. المشروع حالياً في مرحلة التخطيط والتهيئة الأولية، ولا يتضمن نتائج تجريبية بعد.

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

**Planning and Initial Setup**

اكتملت تهيئة الهيكل وخطة التنفيذ فقط. لم تُحدّد مجموعة البيانات النهائية بعد، ولا توجد نتائج تجارب أو دفاتر Jupyter منفذة.

## Future Environment Setup

سيتم التحقق في المرحلة التالية من إصدار Python المناسب، وإنشاء بيئة افتراضية محلية، ومراجعة توافق نطاقات الحزم الموجودة في `requirements.txt` قبل تثبيتها. ستُوثّق أوامر الإعداد بعد اختبارها على بيئة المشروع، لذلك لا يعرض هذا الملف حالياً أوامر تثبيت غير متحقق منها.

## Reproducibility Principles

- إبقاء البيانات الخام دون تعديل وحفظ كل مرحلة معالجة في موقع مستقل.
- استخدام مسارات نسبية وتسجيل إصدارات الحزم ومعاملات التجارب.
- تثبيت بذرة عشوائية موحدة عند وجود عمليات عشوائية.
- تشغيل الدفاتر من البداية إلى النهاية من دون الاعتماد على حالة مخفية.
- توليد القيم والجداول آلياً وعدم تعديل النتائج يدوياً.

## WEKA Comparison Goal

ستُصدّر البيانات المعالجة نفسها إلى تنسيق متوافق مع WEKA، ثم تُضبط عتبات FP-Growth قدر الإمكان لتدقيق القواعد المنطقية ومقاييسها وترتيبها وأسباب أي اختلاف عن Python. لن تُعامل لقطات الشاشة على أنها الدليل الوحيد للمقارنة.

## Data and Results Notice

لم يتم اختيار أو تنزيل أي مجموعة بيانات حتى الآن، ولا توجد أي إحصاءات أو قواعد ارتباط أو نتائج تجريبية في المستودع.
