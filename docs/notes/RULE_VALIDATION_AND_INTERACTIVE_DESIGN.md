# تصميم التحقق من القواعد والمختبر التفاعلي — Phase 5

تاريخ التجميد: 2026-07-13  
الحالة: **مجمّد قبل التنفيذ النهائي**. الحدود التالية اصطلاحات خاصة بالمشروع وليست قوانين علمية عامة.

## لماذا لا تكفي المقاييس الخام؟

Support المرتفع يعني انتشاراً، وConfidence المرتفعة تعني ظهور Consequent كثيراً عند Antecedent، وLift المرتفع يعني تجاوز خط الأساس. لا يثبت أي منها وحده الفائدة التجارية أو السببية. قد ترتفع Confidence لأن Consequent شائع، وقد ترتفع Lift لنمط قريب من Minimum Support لأن المقام صغير. كما أن اتجاه `X → Y` لا يثبت أن X حدث قبل Y داخل الفاتورة.

يميز المشروع بين أربعة محاور:

1. **Metric strength:** قيم Support وConfidence وLift وLeverage وConviction في العينة الأصلية.
2. **Statistical stability:** مدى عودة القاعدة وتقلب مقاييسها تحت Bootstrap transaction resampling.
3. **Redundancy:** هل تضيف القاعدة الأطول دليلاً فوق قاعدة أبسط لنفس Consequent؟
4. **Commercial interpretability:** هل المنتجات والعدد المطلق وصياغة الإجراء قابلة للفهم والاختبار، من دون ادعاء سببي؟

## تصميم Bootstrap

- المصدر هو مصفوفة UK الكاملة: 17,901 معاملة و3,791 منتجاً.
- كل عينة تسحب 17,901 صفاً **مع الإرجاع** على مستوى المعاملة.
- البذور المسجلة: `51001` إلى `51020`، أي 20 عينة أولية.
- يمكن التوسع إلى 30 فقط إذا نجحت العشرين كلها، وكان مجموع زمنها ≤300 ثانية وmedian التشغيل ≤12 ثانية ولم تتجاوز زيادة RSS 2 GiB. هذه الشروط صارمة لمنع توسع غير مبرر؛ وإلا يتوقف المشروع عند 20.
- لا يتجاوز Phase 5 ثلاثين عينة.
- كل عينة تستخدم FP-Growth مستقلاً مع Minimum Support=0.005 و`max_len=3`؛ support count هو دائماً `ceil(0.005 × 17,901)=90`.
- تولد القواعد بالمنطق نفسه المستخدم في Phase 4 وتطابق بمفتاح canonical اتجاهي.
- تحفظ الإخفاقات ولا تستبدل ببذور جديدة.

### تعريف حضور القاعدة

تُعد قاعدة Phase 4 **حاضرة** في عينة Bootstrap إذا أمكن توليدها بالمفتاح نفسه ثم حققت داخل العينة Support≥0.005 وSupport count≥90 وConfidence≥0.70 وLift≥1.20. تسجل المقاييس كلما كان المفتاح قابلاً للتوليد، حتى إن لم يمر بجميع حدود الحضور، كي لا تختفي معلومات عدم اليقين.

معدل الحضور هو عدد العينات الناجحة التي حضرت فيها القاعدة مقسوماً على عدد العينات الناجحة. تصنيفات المشروع:

- Very stable: معدل ≥0.80.
- Moderately stable: من 0.50 إلى أقل من 0.80.
- Weakly stable: من 0.20 إلى أقل من 0.50.
- Unstable: أقل من 0.20.

لكل Support وConfidence وLift تحسب mean وsample standard deviation وpercentiles 2.5% و97.5% وminimum وmaximum وعدد المشاهدات الصالحة. الفواصل **empirical percentile intervals** وليست ضمانات سكانية أو براهين سببية.

## ضوابط الموارد

- حد 120 ثانية لكل Bootstrap run، و100,000 Itemset، و250,000 قاعدة، وزيادة RSS تقريبية 2 GiB.
- لا تستخدم Dense basket؛ تبقى البيانات sparse Boolean.
- تحفظ ملاحظات المرشحين الوسيطة في `data/interim` وتبقى Git-ignored.
- لا يعاد تعدين البيانات عند تحريك عناصر الواجهة؛ تستخدم الواجهات نتائج مسبقة الحساب.
- يسجل كل فشل وسببه وزمنه والبذرة وchecksum لفهارس السحب.

## كشف القواعد المضللة

الأعلام شفافة ولا تعني أن القاعدة "خاطئة":

- `high_confidence_weak_lift`: Confidence≥0.70 وLift<1.50.
- `common_consequent`: Consequent support≥0.08.
- `near_support_floor`: Support count≤112، أي 1.25×90 بعد التقريب.
- `high_lift_low_count`: Lift≥10 وSupport count≤135.
- `weak_bootstrap_stability`: معدل الحضور<0.50.
- `wide_confidence_interval`: عرض percentile interval للثقة≥0.20.
- `wide_lift_interval`: عرض Lift interval أكبر من قيمة mean Lift أو غير صالح.
- `reciprocal_rule_exists`: توجد القاعدة العكسية المباشرة؛ هذا تنبيه قرب منطقي لا إبطال.
- `equivalent_normalized_code`: افتراضياً false لأن Phase 3 يضمن عموداً واحداً لكل StockCode normalized.
- `insufficient_business_evidence`: Unstable أو عدة أعلام جوهرية أو مقاييس ناقصة.

## Redundancy

تُعد القاعدة الأطول subsumed إذا وجدت قاعدة لنفس Consequent وAntecedent أصغر مجموعةً، وكان الفرق المطلق في Confidence≤0.05 ولم يتحسن Lift بأكثر من 10%. تحفظ القاعدة والقاعدة الأبسط والفروق؛ لا تحذف الأدلة الأصلية.

## Evidence tiers والتصرف

يستخدم ترتيب lexicographic، لا درجة سوداء واحدة:

- **Tier A:** Very stable، غير redundant، count≥135، لا interval واسع ولا evidence flag جوهري.
- **Tier B:** Very/Moderately stable، غير redundant، ومقاييس صالحة، لكنه لا يحقق كل شروط A.
- **Tier C:** Weakly stable أو قريب من floor أو redundant؛ يحتاج مراقبة أو تبسيطاً.
- **Tier D:** Unstable أو أدلة ناقصة/مضللة جوهرياً؛ يستبعد من التفسير التجاري القوي.

التصرفات: retain لـA، monitor لـB، simplify للـredundant، reject from business interpretation لـD، وinsufficient evidence للحالات غير الحاسمة. تبقى كل المقاييس والأعلام ظاهرة.

## Corrected scalability

لا يحذف اختبار Phase 4 الأصلي. تستخدم الكسور 25% و50% و75% و100%، والبذور `5501, 5502, 5503` للكسور دون 100%. تختار كل بذرة subset بلا إرجاع، وتستخدم الخوارزميتان الصفوف نفسها.

- **Protocol A — fixed proportion:** Support=0.005؛ يتغير count حسب الحجم. يجيب عن تكلفة النسبة نفسها.
- **Protocol B — fixed absolute count:** Support=`90 / subset_size`؛ يبقى الحد العددي 90. يجيب عن تكلفة شرط دليل عددي ثابت، وقد يكون أكثر صرامة نسبياً في subset الصغير.

كلاهما يستخدم `max_len=3`. لا يدعى أن أحد البروتوكولين صحيح عالمياً؛ إنهما يجيبان سؤالين مختلفين.

## Product Association Network

تستخدم الشبكة قواعد Tier A/B، stable بمعدل≥0.80، nonredundant، وبنية one-product→one-product فقط لتجنب تحويل hyper-rules إلى حواف مضللة. ترتب القواعد حسب tier ثم stability ثم Confidence ثم Lift ثم count، وتعرض بحد أقصى 60 حافة و40 عقدة. حجم العقدة يمثل product support، وعرض الحافة Confidence، وhover يعرض المقاييس والاستقرار. تحسب المكونات والدرجة والدرجة الموزونة وصفياً فقط؛ لا تفسر المركزية كسببية أو أهمية مالية.

## Threshold Explorer

يوفر Jupyter ipywidgets وHTML ذاتي الاكتفاء يعتمد على القواعد المدققة المسبقة، ولا يعيد التعدين. الضوابط: Support وConfidence وLift وstability category وevidence tier وأقصى antecedent length وعدد النتائج. يعرض العدد والملخصات وscatter وLift/stability distributions وجدولاً موجزاً وتحذيراً عند اختيار قواعد ضعيفة أو قريبة من floor. HTML portable لكنه precomputed client-side وليس خدمة تعدين.

## Basket Recommendation Simulator

الأداة **Rule-based Basket Recommendation Simulator** وليست Personalized Recommender أو causal predictor. تطابق قواعد Tier A/B غير redundant التي يكون Antecedent فيها subset من السلة، وتستبعد Consequents الموجودة. الترتيب lexicographic: Tier A قبل B، ثم presence rate وConfidence وLift وsupport count تنازلياً، ثم product code. عند عدة قواعد للمنتج نفسه تعرض أفضل قاعدة وعدد الأدلة المستقلة من دون جمع المقاييس أو عرضها كاحتمال. إذا لم يوجد دليل مؤهل تعيد نتيجة فارغة صراحةً ولا تخترع توصية.

## Business Action Generator

تتحول القواعد المؤهلة فقط إلى **candidates requiring testing**:

- Tier A بطول كلي≥3: Product bundle candidate.
- Tier A one-to-one وcount≥180: Co-display candidate.
- Tier A one-to-one دون ذلك: Cross-sell candidate.
- Tier B: Promotional test candidate.
- Tier C: Monitor for more evidence.
- Tier D: Reject from commercial interpretation.

كل إجراء يحفظ `rule_key` والمقاييس والسبب والقيد وخطوة تحقق مقترحة. لا توجد ادعاءات إيراد أو سببية أو ضمان شراء أو أثر رفوف مثبت.

## حدود الاستخدام

Bootstrap يقيس الاستقرار التجريبي تحت هذه البيانات والتنظيف والعتبات، وليس صلاحية خارجية. Random subsets لا تزيل الانحياز الأصلي. الواجهات أدوات تعليمية تحليلية وليست أنظمة قرار تجاري آلية. تحتاج أي خطوة عملية إلى مراجعة مجال وتجربة مضبوطة. لا يشمل Phase 5 WEKA أو التقرير النهائي أو PDF.
