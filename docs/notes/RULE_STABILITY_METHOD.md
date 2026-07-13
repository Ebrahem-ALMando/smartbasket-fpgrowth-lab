# منهج استقرار قواعد الارتباط

## العينة والإعدادات

يستخدم المنهج مصفوفة UK الكاملة بوصفها مجتمع إعادة السحب التجريبي. لكل seed من 51001 إلى 51020 يسحب NumPy RNG عدد 17,901 row index مع الإرجاع، ثم يشغل FP-Growth مستقلاً عند Support=0.005 و`max_len=3`. يبقى support count 90 في كل عينة. تحفظ البذرة وعدد الصفوف الفريدة وSHA-256 للفهرس والزمن وRSS التقريبي والحالة.

لا تُعد أي عينة فاشلة ناجحة، ولا تستبدل seed. نجحت العشرين كلها. لم يتوسع التشغيل إلى 30 لأن الزمن الإجمالي 385.898 ثانية وmedian 18.876 ثانية تجاوزا الشرطين المجمدين، ولذلك حُترم قرار الموارد بدلاً من تغييره بعد رؤية النتائج.

## Canonical matching والحضور

تولد القواعد من Frequent Itemsets داخل كل resample وتحوّل إلى `antecedent key => consequent key` بترتيب lexical. تُعد قاعدة مرشحة حاضرة إذا ظهر المفتاح وحقق Support≥0.005 وcount≥90 وConfidence≥0.70 وLift≥1.20. تسجل Support وConfidence وLift إذا أمكن توليد المفتاح حتى عند فشل حدود الحضور.

يقسم presence count على عدد العينات الناجحة. حدود Very/Moderate/Weak/Unstable هي اتفاقية المشروع وليست قانوناً عاماً.

## Metric uncertainty

لكل مقياس تحفظ finite observation count وmean وsample standard deviation و2.5th/97.5th percentiles وminimum وmaximum. الفواصل empirical وتعتمد 20 resamples فقط. عدم ظهور القاعدة يقلل عدد observations ولا يعوّض بقيمة صفرية أو تخمين.

النتيجة: 1,911 Very stable، و1,201 Moderately stable، و308 Weakly stable، و3 Unstable. median interval widths: Support=0.00163، Confidence=0.1005، Lift=2.5805.

## القيود

Bootstrap يختبر حساسية إعادة السحب من البيانات نفسها ولا يصحح تحيز المصدر أو الموسمية أو سياسة التنظيف. 20 عينة تحد دقة التقدير، ولا تمثل intervals ضمانات سببية أو خارجية. RSS قبل/بعد ليس peak memory. ملف الملاحظات الوسيط محفوظ في `data/interim` ومُستبعد من Git.
