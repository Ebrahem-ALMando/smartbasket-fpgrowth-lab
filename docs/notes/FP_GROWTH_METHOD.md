# منهج FP-Growth في Phase 4

## المدخلات والتحقق

يحمّل `src/mining/basket_loader.py` مصفوفة UK المحضرة في Phase 3 ويتحقق من أنها CSR بأبعاد `17,901 × 3,791` وبـ473,636 قيمة غير صفرية، وأن كل قيمة تساوي 1، وأن ترتيب الأعمدة والصفوف مطابق لملفات metadata. يتم التحويل إلى pandas Sparse Boolean DataFrame من دون Dense conversion.

## المثال التعليمي

توجد بنية FP-Tree مستقلة وقابلة للقراءة في `fp_tree_educational.py`. تستخدم ست معاملات تعليمية Bread/Milk/Butter/Eggs/Coffee وMinimum Support count=3. تدعم العقد والآباء والأبناء والعدادات وHeader Table وNode-Link وConditional Pattern Bases وConditional Trees والتعدين التكراري ولقطات الإدخال. النتيجة اليدوية ستة Itemsets ويمكن التحقق منها مباشرة؛ لا تستدعي mlxtend ولا تمثل نتيجة UCI.

## البحث عن Minimum Support

جُربت الشبكة `0.05, 0.03, 0.02, 0.015, 0.01, 0.0075, 0.005` بترتيب تنازلي. لكل نقطة سُجل support count وعدد الأنماط حسب الطول ووقت الجدار وRSS التقريبي وعدد القواعد عند Confidence 0.30 و0.50 و0.70 وحالة التنفيذ. اختارت الدالة الحتمية أدنى نقطة ناجحة تحتوي ثنائيات وثلاثيات وتبقى دون الحدود المجمدة.

## التنفيذ النهائي

- الخوارزمية: `mlxtend.frequent_patterns.fpgrowth`.
- البيانات: جميع معاملات UK البالغ عددها 17,901.
- Minimum Support: 0.005، أي 90 معاملة على الأقل.
- Maximum length: 3.
- runtime المسجل في آخر Notebook 04: 23.048 ثانية.
- RSS delta التقريبي: 54,886,400 بايت؛ ليس Peak Memory.
- الناتج: 18,681 Frequent Itemset.

تُحوّل كل Itemset إلى مفتاح lexical ثابت، وتحفظ الأكواد والأوصاف والطول والدعم والعدد. يحسب `support_count = round(support × 17,901)` ويُتحقق منه برمجياً. ترتيب الحفظ: Support تنازلياً ثم الطول والمفتاح بقواعد ثابتة.

## توليد القواعد

تولد `rule_generation.py` جميع القواعد الاتجاهية الممكنة من Itemsets حتى الطول 3 وتحفظ antecedent/consequent support وSupport وConfidence وLift وLeverage وConviction. تحفظ الأكواد مفاتيح ثابتة وتضاف الأوصاف للتفسير. لا توجد قواعد منطقية مكررة بالمفتاح نفسه.

تتطلب القواعد المختارة:

- Support ≥ 0.005 وSupport count ≥ 90؛
- Confidence ≥ 0.70؛
- Lift ≥ 1.20؛
- المقاييس الأساسية finite، وConviction صالحة أو موثقة إذا كانت حدية؛
- عدم سيطرة قاعدة ذات Antecedent أصغر لنفس Consequent مع Confidence وLift غير أقل.

نتج 63,446 قاعدة قبل التصفية و3,423 قاعدة مختارة. حقل interpretation آلي ووصفي، ويذكر أن Lift يقارن مع baseline ولا يثبت السببية.

## القيود

لا تشمل النتائج أنماطاً بطول أربعة فأكثر. لا تعني Association causation أو temporal order. القواعد قرب Support floor قد تكون حساسة لتغير البيانات، ولم ينفذ Bootstrap بعد. لم تُبن شبكة منتجات أو أداة توصية أو WEKA في هذه المرحلة.
