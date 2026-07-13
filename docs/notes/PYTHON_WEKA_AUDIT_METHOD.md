# منهج تدقيق Python وWEKA

## مجموعة المقارنة

يُقرأ `outputs/tables/association_rules_all.csv` ويطبق فقط:

- Support ≥ 0.005.
- Support count ≥ 90.
- Confidence ≥ 0.70.
- مجموع طول antecedent وconsequent ≤ 3.

لا يطبق Lift ≥ 1.20 ولا bootstrap stability أو evidence tiers من Phase 5. الناتج 3,468 قاعدة Python. ينتج WEKA 3,468 قاعدة بالحدود المنطقية نفسها.

## Canonicalization

كل alias من الشكل `P_000000` يُعكس بواسطة `weka/datasets/product_attribute_mapping.csv`. تُرتب StockCodes داخل كل طرف lexical وتبنى `rule_key` بالدالة نفسها المستخدمة في Python: `antecedent itemset_key => consequent itemset_key`. يحتفظ الجدول canonical بالنص الأصلي، aliases، descriptions، counts، metrics الأصلية، ومصدر support المشتق صراحة من `joint_count / 17901`.

أي alias مجهول يبقى كسطر `mapping_valid=False`. لا يحذف duplicate منطقي قبل عدّه. في النتيجة الفعلية: mapping failures=0 وduplicate rule keys=0.

## Tolerances

- identity وsupport count: exact.
- Support/Confidence/Lift/Leverage: absolute `1e-12`.
- Conviction: absolute وrelative `1e-10`، مع infinity صريح.

تُفصل المساواة exact عن tolerance match. يُحسب absolute وrelative difference لكل metric لكل قاعدة مشتركة. ترتيب المصدر يقارن منفصلًا ولا يؤثر في identity.

## النتائج

- Python=3,468، WEKA=3,468، common=3,468، Python-only=0، WEKA-only=0.
- Support: 6 exact و3,462 tolerance؛ maximum absolute difference `9.97466e-17`.
- Confidence: 2,903 exact و565 tolerance؛ maximum `3.33067e-16`.
- Lift: 2,989 exact و479 tolerance؛ maximum `4.26326e-14`.
- Leverage: 3,468 exact؛ maximum `0`.
- Conviction: 3,468 material metric-definition mismatches؛ maximum absolute `9.3216859393` وrelative `0.25`.
- إجمالي metric values: 9,366 exact، 4,506 tolerance، 3,468 definition mismatches.

لأن Conviction تختلف في كل قاعدة، فإن rule-wide all-metric status هو mismatch لـ3,468 قاعدة، رغم تطابق identity وsupport counts وتوافق المقاييس الأربعة الأخرى exact/within tolerance. لا تُخفى هذه النتيجة بإعادة اشتقاق metric بدل الأصل.

## دليل تعريف Conviction

يكشف source المرفق في `weka-src.jar` أن WEKA 3.8.7 يحسب:

```text
[premise_count × (N − consequence_count) / N] /
(premise_count − joint_count + 1)
```

بينما mlxtend يستخدم الصيغة غير الملساء `(1 − consequent_support) / (1 − confidence)`، المكافئة لمقام `premise_count − joint_count` بلا `+1`. قيمة WEKA API تطابق صيغة المصدر من counts بفارق أقصى `3.55e-15`، وقيمة Python تطابق الصيغة غير الملساء بفارق أقصى `1.28e-13`. تحفظ القيم الأصلية والمشتقة الموسومة ودليل الصيغ، ولا تعد Conviction «rounding».

