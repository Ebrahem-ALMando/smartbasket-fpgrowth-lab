# تحليل فروق Python وWEKA

## مصفوفة التصنيف

| الجانب | التصنيف | الدليل والنتيجة |
|---|---|---|
| هوية 3,468 قاعدة وsupport counts | exact agreement | common=3,468؛ لا unmatched ولا duplicate ولا mapping failure. |
| Support proportion | numeric rounding only | count-derived WEKA مقابل floats المخزنة؛ maximum `9.97e-17` وضمن `1e-12`. |
| Confidence | numeric rounding only | maximum `3.33e-16`؛ لا boundary failure. |
| Lift | numeric rounding only | maximum `4.26e-14`؛ لا mismatch خارج tolerance. |
| Leverage | exact agreement | كل 3,468 قيمة exact. |
| Conviction | metric-definition difference | WEKA يضيف `+1` إلى مقام count؛ Python لا يفعل. كل القيم تختلف ماديًا. |
| ترتيب القواعد | output-order difference | لا رتبة source متساوية؛ median absolute rank difference `952.5` وmaximum `3,419`. الهوية مع ذلك كاملة. |
| Support boundary 0.005/count 90 | exact agreement | لا Python-only/WEKA-only؛ الحد شامل في التنفيذين. |
| Upper support diagnostic | resolved parameter-semantic issue | `-U 0.005` أعطى فقط 137 قاعدة ذات count=90؛ المحاذاة الصحيحة `-U 1.0`. |
| Sparse positive value | exact agreement | WEKA probe عدّ 473,636 positive stored values و3,791 binary attributes. |
| Product aliases/transaction order | exact agreement | checksums والعينات الحتمية متطابقة؛ mapping failures=0. |
| Implementation difference | Conviction فقط ضمن المقاييس المدققة | موثق بصيغة source الفعلية؛ لا حذف للقواعد. |
| Export or mapping issue | none | لا malformed/empty rows ولا aliases مجهولة. |
| Unresolved | none material | runtime variability وmemory approximation قيود قياس وليستا فرق صحة غير محلول. |

## تفسير الترتيب

يرتب Python export أولًا حسب Support ثم Confidence ثم Lift ثم key. WEKA يرتب عرض القواعد أساسًا حسب primary metric Confidence مع tie behavior داخلي. لذلك اختلاف rank متوقع ولا يعني اختلاف rule identity. يوضح scatter مستقل هذا الفرق ولا يُستخدم الترتيب لمطابقة القواعد.

## ما لم يحدث

لم تُحذف القواعد غير المطابقة، ولم يتغير support/confidence لإجبار النتيجة، ولم تطبق filters الخاصة بـ Phase 5. تصحيح `-U` موثق بنتيجة diagnostic وبمعنى أن Python لا يملك maximum-support ceiling. لا يوصف فرق Conviction بأنه rounding لأنه يتبع صيغة مختلفة ويمكن إعادة إنتاجه من counts.

