# سجل قرارات Phase 6

## الحالة الأولية

- branch `main`، HEAD `c6453b9855ce6512b8d4bcc9910c45bda80cdc29`، working tree clean.
- لا Java/WEKA/WEKA_PATH ولا مخرجات WEKA سابقة عدا `.gitkeep`.
- Python artifacts: 17,901 × 3,791 binary CSR و473,636 presence؛ 63,446 raw rules و3,468 core-aligned rules.
- لم تُعدّل مخرجات Python أو Git history/remotes.

## البيئة والمصدر

- WEKA 3.8.7 stable الرسمية، installer bytes `175,667,998`, SHA-256 `3f18d585bd624cb1c6410ee1609f9966e7da0cbcddc9b7bd89dd0027a656c29a`.
- `weka.jar` bytes `14,653,641`, SHA-256 `621054b25a950e5c61c04e859d0ca5fad5bde55435a1a4633144389d44ec52d5`.
- BellSoft OpenJDK 25.0.2+12 LTS amd64 runtime؛ bundled `javac` غير متاح.
- matching BellSoft JDK ZIP bytes `248,924,791`, SHA-256 `704e5d6ff0b6de67461d12403a9864d211fa9c64187efa185dfa70dfbb130f33`; `javac 25.0.2`.
- installer وضع نسخة افتراضية غير مقصودة في Program Files؛ نُقلت التوزيعة إلى project-local path وأزيلت النسخة الافتراضية بالـ uninstaller الرسمي. التنفيذ الحالي لا يحتاج admin/system install.

## ARFF

- sparse nominal `{0,1}`؛ omitted=absence والقيمة الصريحة `1`=presence.
- aliases رقمية حتمية `P_000000`؛ descriptions لا تدخل identifiers.
- file bytes `3,310,260`, SHA-256 `f1fb8eda9c06c14720dcfbc3a81f8509eefc40ab9da956934fe2283a5c9378f7`.
- 17,901 instances، 3,791 attributes، 473,636 presences؛ لا empty/malformed rows.
- سبع عينات rows وسبع attributes متطابقة، وorder checksums متطابقة.
- WEKA probe حمّل الملف وأكد counts نفسها.

## خيارات التنفيذ

`-P 2 -I 3 -N 1000000 -T 0 -C 0.70 -U 1.0 -M 0.005 -D 0.005 -S` مع `-Xmx4g` وflag launcher الرسمي `--add-opens=java.base/java.lang=ALL-UNNAMED`.

قرار `-U 1.0` ليس تخفيفًا للـ minimum support: diagnostic موثق بقيمة 0.005 أعاد 137 قاعدة كلها joint count=90، ما أثبت أنه سقف قبول. Python لا يملك سقفًا، لذلك 1.0 هو alignment الصحيح. `-S` يجعل top-N وdelta غير حاكمين.

## نتائج القواعد والتدقيق

- bridge وCLI: 3,468 rule؛ Python: 3,468؛ common: 3,468؛ unmatched=0.
- support counts exact؛ mapping/duplicate/parsing failures=0.
- Support/Confidence/Lift ضمن tolerance وLeverage exact.
- Conviction تختلف في 3,468 قاعدة بسبب WEKA `+1` smoothing؛ maximum absolute `9.3216859393`, relative `0.25`.
- ordering مختلف كليًا عن rank Python لأن sorting policies مختلفة؛ لا يؤثر في identity.
- لا فرق مادي unresolved.

## Runtime

Warm-up + 3 measured لكل تنفيذ. Python median loading/mining/end-to-end: `0.920726 / 16.144838 / 17.452942` s. WEKA: `0.374842 / 12.517578 / 13.533139` s، startup التقريبي `0.230352` s. لا يُستنتج تفوق عام: representations، JVM/JIT، parsing، process lifecycle، export، وmemory semantics مختلفة. memory observations ليست peaks.

## GUI والتقرير اللاحق

Explorer launcher والدليل موجودان؛ GUI متاحة. screenshots لم تُلتقط آليًا وبقيت checklist يدوية. Notebook 08 يوثق النتائج. لم يبدأ final HTML/PDF report، ولم يبدأ Phase 7. القرار المؤجل للتقرير النهائي هو طريقة عرض لقطة Explorer والتحذير المرئي حول تعريف Conviction وحدود runtime comparison.

