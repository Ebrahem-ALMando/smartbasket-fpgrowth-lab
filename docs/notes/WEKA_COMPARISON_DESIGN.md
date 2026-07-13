# تصميم مقارنة Python وWEKA

**الحالة:** مجمّد قبل تنزيل WEKA أو تنفيذ التعدين النهائي.  
**التاريخ:** 2026-07-14.  
**النطاق:** Phase 6 فقط.

## الهدف وحدود الادعاء

تُستخدم WEKA بوصفها تنفيذًا مستقلاً من University of Waikato لتدقيق تجربة FP-Growth المنفذة في Python، لا بوصفها مرجعًا معصومًا ولا كبديل عن سلسلة المعالجة الموثقة. تميّز المقارنة بين ثلاثة مفاهيم:

1. **Algorithm equivalence:** تطبيق المنهجين لفكرة FP-Growth وقواعد الارتباط نفسها.
2. **Implementation equivalence:** تطابق قرارات التنفيذ مثل تفسير الحدود، توليد القواعد، الدقة العددية، والترتيب. لا يُفترض مسبقًا.
3. **Output-format equivalence:** تطابق شكل النص أو ترتيب الأسطر. هذا غير مطلوب لإثبات تطابق القواعد المنطقية.

لقطات شاشة Console أو Explorer غير كافية وحدها؛ لأنها لا تثبت اكتمال القواعد، ولا تسمح بتدقيق mapping أو القيم العددية آليًا. الدليل الأساسي سيكون ARFF موثقًا، Java API bridge، ملفات machine-readable، وسجل CLI مستقل.

## مجموعة بيانات Python المجمدة

- Scope: United Kingdom بعد سياسة التنظيف المعتمدة.
- Transactions: 17,901 بترتيب الصفوف المحفوظ في `data/processed/online_retail_transaction_index.csv`.
- Products: 3,791 بترتيب الأعمدة المحفوظ في `data/processed/online_retail_basket_columns.json`.
- Binary CSR presence count: 473,636.
- Minimum Support: `0.005` مع شرط صريح `support_count >= 90` في audit.
- Minimum Confidence: `0.70` شاملًا للحد.
- Maximum total itemset/rule size: `3`.
- لا يطبق core equivalence audit شرط Lift الخاص بالتفسير في Phase 5 ولا stability/evidence filters.
- جدول Python المرجعي هو `outputs/tables/association_rules_all.csv` بعد الفلاتر المنطقية المتطابقة، دون تعديل مخرجات Python السابقة.

## تمثيل WEKA المخطط

سيُصدّر basket نفسه إلى sparse ARFF. كل منتج attribute اسمي binary بالقيم `{0,1}`؛ القيمة الأولى `0` هي absence/default المحذوفة من sparse row، والقيمة الثانية `1` هي presence الصريحة. لا يوجد class attribute ولا وصف منتج داخل اسم attribute.

يُنشأ alias حتمي وآمن من رقم العمود، مثل `P_000000`، ويُحفظ mapping صريح بين `column_index`, alias, `StockCode`, و`Description`. الاعتماد على رقم العمود يمنع collisions حتى عندما يحتوي StockCode رموزًا غير آمنة في ARFF. يُحفظ transaction mapping منفصل، ولا يعاد ترتيب الصفوف أو الأعمدة عند التصدير.

## خطة التطابق المنطقي

قبل التعدين تُفحص الأمور الآتية:

- WEKA يحمّل ARFF ويبلغ 17,901 instances و3,791 attributes.
- complete sparse-value count يساوي 473,636.
- جميع attributes nominal binary والقيمة الموجبة index 2 في واجهة WEKA ذات الفهرسة البشرية.
- عينات حتمية من الصفوف والمنتجات تطابق CSR وmapping.
- checksums مستقلة لترتيب transaction IDs وترتيب product codes تطابق export metadata.
- لا توجد صفوف فارغة أو malformed.

أي فشل منطقي يوقف التعدين؛ لا يُسمح بتعويضه بتغيير scope أو حذف منتجات.

## خطة محاذاة FPGrowth

ستُقرأ option help من الإصدار المثبت فعليًا قبل اختيار CLI flags. يُضبط Java bridge عبر API ويُسجل effective configuration:

- lower minimum-support bound = `0.005`.
- upper support bound يساوي الحد نفسه عند الحاجة لمنع support-decrease search من تغيير التجربة.
- delta موثق وغير مؤثر عندما يتساوى الحدّان.
- metric = Confidence.
- minimum metric = `0.70`.
- maximum items = `3` وفق semantics الفعلية للإصدار.
- positive value = nominal `1`، مع التحقق من index الفعلي.
- find-all-rules mode مفعّل حتى لا تصبح النتيجة top-N اعتباطية.

لن يُستخدم option غير موجود في help الفعلي، ولن يتغير أي parameter بصمت لإجبار التطابق. إذا تعذر تمثيل حد Python تمامًا تُسجل الفجوة قبل التنفيذ وتظهر في audit.

## استخراج القواعد وCanonicalization

Java AssociationRules API هو المصدر الأساسي متى كان متاحًا. يُحفظ WEKA human-readable model أيضًا، لكن لا يُحلل بدل API إلا كخطة fallback موثقة. يحتفظ raw export بأسماء aliases، counts، عدد المعاملات، وكل metric متاحة. في Python يعكس mapping كل alias إلى StockCode، ثم تُرتب عناصر الطرفين lexical وتُبنى `rule_key` بواسطة الصيغة نفسها المستخدمة في `src/mining/rule_generation.py`.

لا تُشتق metric مفقودة إلا بصيغة موثقة ومن counts متاحة، وتوسم حينها `derived`. أي alias مجهول، rule مكرر، أو parse failure يظهر كفشل صريح ولا يُحذف بصمت.

## Tolerances والمقارنة

الهوية المنطقية وsupport counts يجب أن تكون exact. الحدود العددية الأولية المخططة، ويمكن تضييقها فقط بناءً على دقة المصدر لا لتجميل النتائج:

- support proportion absolute tolerance: `1e-12` عند الاشتقاق من counts نفسها.
- confidence, lift, leverage absolute tolerance: `1e-12` لقيم API الكاملة.
- conviction absolute tolerance: `1e-10` مع relative tolerance `1e-10`، ومعالجة infinity صراحة.
- exact metric match: bitwise/قيمة float متساوية بعد parsing.
- tolerance match: ليست exact لكنها داخل tolerance المعلن.

تُفصل rule identity عن ordering، وتُحفظ Python-only وWEKA-only دون حذف. كل فرق مادي يُصنف بالدليل إلى rounding، ordering، threshold boundary، metric definition، implementation، export/mapping، أو unresolved.

## Runtime methodology وحدوده

تُنفذ warm-up واحدة وثلاث measured runs عندما تسمح الموارد. في Python يُفصل basket loading عن mining، وفي WEKA يُفصل Java process startup تقريبًا عن ARFF loading وFPGrowth mining وrule export. يُعرض algorithm-only إلى جانب end-to-end. تمثيل Python CSR/pandas sparse يختلف عن sparse ARFF/Java objects؛ لذا لا تعني الأزمنة تفوقًا عامًا.

Java startup، JIT warm-up، package initialization، ARFF parsing، garbage collection، وتصدير آلاف القواعد overheads مستقلة يجب تسجيلها. قياس الذاكرة تقريبي (process/JVM observations) وليس peak profiler measurement. GUI ليس مسار benchmark؛ التنفيذ البرمجي وCLI قابلان لإعادة الإنتاج، بينما Explorer للعرض الصفي فقط.

## بيئة التنفيذ والمصدر

أظهر الفحص الأولي عدم وجود `java`, `javac`, `WEKA_PATH`, أو `weka.jar`. سيُستخدم الإصدار stable الرسمي الذي تعلنه صفحة University of Waikato وقت التنفيذ، ويفضل Windows x64 distribution الرسمي ذي JVM المضمّن، موضوعًا محليًا تحت `tools/weka/`. لا system-wide installation ولا admin privileges. تُسجل URL، version، filename، bytes، SHA-256، retrieval date، Java vendor/version/architecture، ومسار jar. تبقى binaries خارج Git.

## Resource safeguards وسياسة الفشل

- لا dense ARFF ولا dense DataFrame كامل.
- الكتابة streaming للـ ARFF وقراءة CSR row-wise.
- heap limit صريح مناسب (يبدأ بـ 4 GiB إن كان متاحًا) ويسجل في الأوامر.
- timeout واضح لكل تشغيل، مع حفظ stderr وexit code.
- validation قبل التعدين، وschema validation بعد export.
- لا إعادة تشغيل بمعاملات مختلفة دون تسجيل run جديد وسبب واضح.

إذا تعذر تنزيل المصدر الرسمي، أو تطلب installer تفاعلًا لا يمكن أتمتته بأمان، يتوقف العمل ويُذكر الإجراء اليدوي. إذا لم يتوفر `javac` في التوزيعة المضمّنة، تُفحص JShell أو precompiled/script route رسمي؛ لا يُثبت compiler غير مرتبط أو artifact غير رسمي. إذا لم تدعم AssociationRules API metric معينة، تُسجل unavailable ولا تُفبرك. لا يبدأ Phase 7 ولا التقرير النهائي في هذه المرحلة.

## ملحق ما بعد التجميد: تصحيح Upper Support قبل التنفيذ النهائي

أُجري تشغيل diagnostic بعد قراءة help الفعلي وبالقيمة المخططة أولًا `-U 0.005`. أنتج 137 قاعدة فقط، وكانت `total_support_count = 90` لكل قاعدة بلا استثناء. يثبت هذا أن مساواة upper bound بالحد الأدنى لا «تثبّت البحث» في find-all mode، بل تفرض سقف قبول يقارب 90 أيضًا، فتستبعد القواعد ذات الدعم الأكبر. احتُفظ بسجل هذا التشغيل تحت `tools/weka/runs/` وبملخص صغير في نتائج WEKA.

لأن Python يفرض حدًا أدنى فقط ولا يفرض maximum support، صُححت المحاذاة قبل التنفيذ النهائي إلى `-M 0.005` و`-U 1.0`. يبقى `-S` مفعّلًا، ولذلك لا تُستخدم iterative support reduction ولا top-N. هذا تعديل معلن مدعوم بنتيجة diagnostic، وليس تغييرًا صامتًا لإجبار التطابق؛ وسيظهر في parameter-alignment وdifference-analysis.
