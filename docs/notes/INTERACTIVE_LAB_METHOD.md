# منهج المختبر التفاعلي

## Threshold Explorer

تعمل نسخة Jupyter عبر ipywidgets، وتعمل نسخة HTML client-side مع Plotly مضمن. كلاهما يرشح `rule_quality_audit.csv` ولا يستدعي FP-Growth أو Apriori. الضوابط هي Support وConfidence وLift وStability category وEvidence tier وأقصى Antecedent length وعدد النتائج. تعرض الواجهة عدد القواعد وscatter وLift distribution وstability counts وجدولاً وتحذيراً للقواعد القريبة من floor.

الـHTML ذاتية الاكتفاء، لكنها ليست خادم تعدين ولا تعيد حساب thresholds غير الموجودة. توجد ثلاثة presets موثقة، وتبقى جميع القرارات قابلة لإعادة الإنتاج من الجدول.

## Product Association Network

تبدأ الشبكة من قواعد Very stable ذات presence≥0.80 وConfidence≥0.70 وLift≥1.20 ومن Tier A/B وغير redundant. تقبل one-product→one-product فقط لأن تحويل hyper-rule إلى عدة edges قد يوحي بعلاقات لم تُقَس منفردة. يرتب الفلتر حسب tier ثم stability وConfidence وLift وcount ويقف عند 60 edge و40 node.

حجم node يمثل product support، وعرض edge يمثل Confidence، وhover يعرض rule وSupport count وLift والاستقرار وtier. تحفظ الأكواد داخلياً والأوصاف للعرض. تحسب degree وweighted degree وweak component وصفياً؛ لا تعني causality أو financial importance. الناتج 40 عقدة و60 حافة و14 مكوناً.

## Basket Recommendation Simulator

الأداة rule-based وغير شخصية، ولا تستخدم CustomerID. تطابق Antecedent subset، تستبعد Consequent الموجود، وتستخدم Tier A/B stable nonredundant rules فقط. الترتيب: Tier A، ثم presence، ثم Confidence، ثم Lift، ثم count، ثم code. إذا دعمت عدة قواعد المنتج نفسه تعرض أفضلها وعدد قواعد الدعم من دون جمع المقاييس كاحتمال.

يوفر Python resolver للكود أو substring في الوصف، وwidget، وHTML محمولة، وأمثلة مولدة من قواعد فعلية. المدخل غير المعروف ينتج خطأً واضحاً، وغياب الدليل ينتج جدولاً فارغاً/رسالة no result. لا تُختلق توصية.

## الحدود

كل الأدوات وسائل تعليمية تحليلية. لا تقدم تخصيصاً أو توقع شراء أو سببية أو أثر إيراد. HTML لا تحفظ تعديلات المستخدم ولا تتصل بخادم، وwidgets تتطلب إعادة Run All بعد Restart Kernel. يلزم اختبار خارجي قبل أي استخدام تجاري.
