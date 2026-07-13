# دليل عرض WEKA Explorer

## تشغيل الواجهة

1. من PowerShell داخل جذر المشروع شغّل `weka/run_weka_gui.ps1`.
2. في **WEKA GUIChooser** اختر **Explorer**.
3. من تبويب **Preprocess** اختر **Open file...** وحمّل `weka/datasets/online_retail_uk_binary_sparse.arff`.
4. تحقق أن أعلى الشاشة يعرض **Instances: 17901** و**Attributes: 3791**. لا تحدد class attribute.
5. افتح تبويب **Associate**.
6. اضغط اسم associator واختر `weka.associations.FPGrowth`.
7. افتح option dialog واضبط القيم التالية كما في التنفيذ البرمجي:

   - `positiveIndex = 2`.
   - `maxNumberOfItems = 3`.
   - `numRulesToFind = 1000000`؛ هذه القيمة لا تتحكم بالنتيجة لأن find-all مفعّل.
   - `metricType = Confidence`.
   - `minMetric = 0.70`.
   - `upperBoundMinSupport = 1.0`، لأن Python لا يفرض upper support ceiling.
   - `lowerBoundMinSupport = 0.005`.
   - `delta = 0.005`؛ غير مستخدم عند find-all.
   - `findAllRulesForSupportLevel = True`.
   - اترك transactions/rules must-contain فارغين و`useOR=False`.

8. راجع option summary قبل التشغيل؛ يجب أن يكافئ `-P 2 -I 3 -N 1000000 -T 0 -C 0.70 -U 1.0 -M 0.005 -D 0.005 -S`.
9. اضغط **Start**. يجب أن يبدأ output بـ `FPGrowth found 3468 rules` في البيئة المجمدة.
10. اقرأ كل قاعدة بوصفها premise count ثم consequence/joint count، مع conf/lift/lev/conv. تذكر أن Conviction في WEKA تستخدم smoothing `+1` وتختلف عن mlxtend.
11. انقر بالزر الأيمن على run داخل Result list واختر **Save result buffer** واحفظ نسخة العرض باسم واضح، دون استبدال ملفات bridge.
12. طابق screenshot للخيارات مع `weka/results/weka_effective_options.json` قبل استخدامه في العرض.

## Screenshot checklist اليدوي

- [ ] GUIChooser أو Explorer ظاهر ومحمل.
- [ ] dimensions: 17,901 instances و3,791 attributes ظاهرة.
- [ ] FPGrowth option dialog ظاهر بكل القيم أعلاه، وخاصة `-U 1.0`, `-M 0.005`, وfind-all.
- [ ] Association output ظاهر ويعرض 3,468 rules.
- [ ] Result buffer محفوظ.
- [ ] لا تظهر بيانات شخصية أو مسارات مستخدم حساسة في اللقطة.

الواجهة متاحة بواسطة launcher، لكن لم تُنفذ GUI automation ولم تُفبرك screenshots. التقاطها خطوة عرض يدوية؛ الدليل العلمي الأساسي هو bridge/API وCLI والـ audit المحفوظ.

