# سجل قرارات Phase 5

تاريخ التنفيذ: 2026-07-13  
الحالة: مكتمل ضمن الاستقرار والجودة والمختبر التفاعلي والتفسير الحذر؛ لم تبدأ Phase 6 أو WEKA.

## Bootstrap والاستقرار

- نُفذت 20 عينة transaction-level بالحجم الكامل 17,901 معاملة وبالإرجاع.
- البذور: 51001 إلى 51020، وكل sample index له SHA-256 محفوظ.
- نجحت 20/20 ولم توجد عينات فاشلة أو مستبدلة.
- الزمن الإجمالي 385.898 ثانية، median 18.876 ثانية، والحد الأقصى 23.329 ثانية.
- لم يحدث التوسع إلى 30 لأن مجموع الزمن وmedian تجاوزا بوابتي 300 و12 ثانية المجمدتين، رغم نجاح التشغيلات.
- بقي Minimum Support=0.005 وcount=90 و`max_len=3` في كل عينة.
- قيّمت جميع قواعد Phase 4 المرشحة وعددها 3,423.

نتيجة الاصطلاحات المجمدة:

| الفئة | العدد |
|---|---:|
| Very stable | 1,911 |
| Moderately stable | 1,201 |
| Weakly stable | 308 |
| Unstable | 3 |

كان median عرض interval 2.5%–97.5% مساوياً 0.00163 لـSupport و0.1005 لـConfidence و2.5805 لـLift. متوسط عدد مشاهدات المقاييس الصالحة 17.22 من 20؛ عدم ظهور المفتاح في بعض العينات جزء من دليل عدم الاستقرار وليس قيمة مفقودة مخفية.

## جودة القواعد وRedundancy

- حملت 2,802 قاعدة علماً واحداً على الأقل؛ الأعلام متداخلة ولا تعني البطلان تلقائياً.
- 2,082 قاعدة جمعت Lift≥10 مع count≤135، و1,975 كانت قرب floor≤112، و646 لها Consequent support≥0.08، و311 حضورها<0.50.
- لم تظهر حالة Confidence≥0.70 مع Lift<1.50 داخل مرشحي Phase 4 لأن Phase 4 كان قد اشترط Lift≥1.20 وكانت القيم الفعلية أعلى من حد العلم؛ بقي الكاشف دفاعياً ومختبراً.
- كشف معيار subsumption عدد 255 قاعدة أطول لا تضيف تحسناً كافياً فوق قاعدة أبسط لنفس Consequent.
- بقي 2,871 قاعدة stable/nonredundant ومؤهلة Tier A/B للتفسير الحذر.

توزيع Evidence tiers: Tier A=590، Tier B=2,281، Tier C=549، Tier D=3. لا تستخدم درجة opaque؛ الترتيب يعتمد الاستقرار ثم redundancy والعدد المطلق وعرض الفواصل والأعلام.

## Corrected scalability

نُفذت 40 مقارنة، كلها ناجحة، باستخدام الكسور 25% و50% و75% و100% والبذور 5501 و5502 و5503 دون 100%. استخدم FP-Growth وApriori row-index checksum نفسه في كل مقارنة.

- Protocol A ثبت Support=0.005؛ counts: 23 و45 و68 و90. كانت medians لعدد Itemsets: 20,480 و18,825 و19,211 و18,681.
- Protocol B ثبت count=90؛ medians: 412 و2,187 و7,415 و18,681.
- anomaly الأصلي 138,140 عند time prefix 25% بقي محفوظاً. الفرق مع median العشوائي 20,480 يوضح أثر التركيب الزمني والحد العددي، لا خطأً يجب حذفه.
- Protocol A وB يجيبان سؤالين مختلفين؛ لا يُعلن أحدهما معياراً عالمياً.

## المختبر التفاعلي

- Threshold Explorer يرشح 3,423 قاعدة مسبقة الحساب ولا يعيد التعدين.
- Product Association Network تستخدم Very stable، Tier A/B، nonredundant، one-to-one rules فقط؛ 40 عقدة و60 حافة و14 مكوناً ضعيف الاتصال، مع أكبر مكون من 6 عقد.
- Basket Simulator يستخدم 2,871 قاعدة مؤهلة ويرتب lexicographically حسب tier ثم presence وConfidence وLift وcount. يمكنه إعادة نتيجة فارغة.
- HTML الثلاث ذاتية الاكتفاء/محمولة؛ Explorer client-side وليس خادم تعدين، وwidgets تحتاج Run All بعد Restart Kernel.

## Business Action Generator

أنشأ المولد مرشحين موصولين بكل `rule_key`:

- Product bundle candidate: 515.
- Cross-sell candidate: 17.
- Co-display candidate: 58.
- Promotional test candidate: 2,281.
- Monitor for more evidence: 549.
- Reject from commercial interpretation: 3.

هذه ليست إجراءات مثبتة تجارياً. كل صف يصرح بعدم السببية أو قياس الإيراد ويقترح تجربة مضبوطة أو مراقبة.

## القرارات المؤجلة

- إعداد WEKA وتشغيله وتوحيد تمثيل البيانات والمعاملات.
- تدقيق Python versus WEKA للقواعد والمقاييس والأداء.
- اختبارات تجارية أو زمنية خارج dataset، وBootstrap أكبر إذا توفر مبرر وموارد.
- التقرير HTML النهائي وPDF النهائي.
