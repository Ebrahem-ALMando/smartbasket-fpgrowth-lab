# منهج تنفيذ WEKA

## البيئة المثبتة محليًا

استُخدمت WEKA 3.8.7 stable الرسمية مع BellSoft OpenJDK Runtime 25.0.2+12 LTS (amd64). توجد التوزيعة portable في `tools/weka/distribution/` وتبقى Git-ignored. لأن runtime المرفقة لا تحتوي `javac` أو JShell، جُمّع bridge بواسطة Liberica Standard JDK 25.0.2+12 المطابق من BellSoft تحت `tools/weka/jdk/`، ثم نُفّذ دائمًا بواسطة runtime المرفقة مع WEKA. لا يعتمد المشروع على system PATH أو `JAVA_HOME`.

سُجلت المصادر والأحجام وSHA-256 في `tools/weka/source_metadata.json`. jar الفعلية هي `tools/weka/distribution/weka.jar` وإصدارها 3.8.7 وSHA-256 لها `621054b25a950e5c61c04e859d0ca5fad5bde55435a1a4633144389d44ec52d5`.

## التحقق من التنفيذ والخيارات

ثبت وجود `weka.associations.FPGrowth` بالتنفيذ الفعلي. حُفظ help الحقيقي في `weka/results/weka_fpgrowth_help.txt`. يثبت help أن:

- `-P 2`: positive value، وIndex 2 هو المستخدم دائمًا للـ sparse instances.
- `-I 3`: maximum items داخل large itemsets والقواعد.
- `-N`: required top-N، لكنه لا يتحكم بالنتيجة عند تفعيل `-S`.
- `-T 0`: Confidence.
- `-C 0.70`: minimum metric.
- `-U 1.0`: upper support ceiling غير مقيّد بالنسبة لمقارنة Python.
- `-M 0.005`: lower minimum support.
- `-D 0.005`: delta مسجل لكنه غير مستخدم في find-all mode.
- `-S`: كل القواعد التي تحقق lower support وmetric؛ يعطل iterative top-N search.

أثبت diagnostic أن `-U 0.005` يستبعد كل قاعدة ذات count أكبر من 90 وينتج 137 قاعدة فقط، كلها count=90. لذلك القيمة المحاذية لـ Python، الذي لا يفرض maximum support، هي `-U 1.0`. حفظ الملخص في `weka/results/weka_diagnostic_upper_bound_005.json`.

## Java bridge

المصدر القابل للمراجعة هو `weka/java/WekaFPGrowthBridge.java`. يجمع بالأمر المكافئ:

```powershell
tools/weka/jdk/jdk-25.0.2/bin/javac.exe -encoding UTF-8 `
  -cp tools/weka/distribution/weka.jar `
  -d weka/java/classes `
  weka/java/WekaFPGrowthBridge.java weka/java/WekaArffProbe.java
```

يحمّل bridge sparse ARFF عبر `DataSource`, ويعيد فحص 17,901 instance و3,791 binary nominal attribute و473,636 presence، ثم يضبط FPGrowth بالـ API. يُستخرج `AssociationRules` و`AssociationRule` مباشرة، لا من console text. يحفظ aliases، side/joint counts، N، Confidence، Lift، Leverage، Conviction، primary metric، وكل metric names/values.

تُقاس loading وmining وrule export داخل JVM، ويقاس process wall خارجها؛ الفرق التقريبي هو startup. الذاكرة هي JVM used-memory observation بعد العمل وليست peak profiler measurement. استُخدم `-Xmx4g` وflag الموجود في launcher الرسمي `--add-opens=java.base/java.lang=ALL-UNNAMED`. stdout وstderr النهائيان محفوظان، وكلا stderr فارغ.

## التشغيلات والنتائج

نُفذت warm-up واحدة وثلاث measured runs، كل منها JVM جديدة. القواعد في جميع التشغيلات: 3,468 بلا فشل. measured mining seconds: `10.640594`, `12.517578`, `18.906375`; الوسيط `12.517578`. وسيط loading `0.374842`، startup التقريبي `0.230352`، end-to-end `13.533139` ثانية. أكبر observation للذاكرة ضمن measured runs `155,441,640` bytes.

الملفات الأساسية:

- `weka/results/weka_rules_raw.csv`
- `weka/results/weka_console_output.txt`
- `weka/results/weka_run_metadata.json`
- `weka/results/weka_effective_options.json`
- `weka/results/weka_runtime_runs.csv`

## CLI الرسمي

شُغلت class الرسمية مستقلة بالخيارات نفسها: `-P 2 -I 3 -N 1000000 -T 0 -C 0.70 -U 1.0 -M 0.005 -D 0.005 -S`. exit code هو 0، wall time `17.144040` ثانية، وconsole أعلن 3,468 قاعدة. حُفظ الأمر النسبي، stdout، stderr، Java/WEKA versions في ملفات `weka_cli_*`; stderr النهائي فارغ. bridge هو الدليل machine-readable الأساسي وCLI دليل ثانوي.

