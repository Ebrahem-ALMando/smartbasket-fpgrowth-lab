# مصدر WEKA وبيئة Java

## التوزيعة الرسمية

استُخدمت **WEKA 3.8.7 stable** من University of Waikato. صفحة التنزيل الرسمية هي:

- <https://waikato.github.io/weka-wiki/downloading_weka/>
- الملف الرسمي المشار إليه للـ Windows x64: <https://prdownloads.sourceforge.net/weka/weka-3-8-7-bellsoft-x64-windows.exe>

تعلن الصفحة أن سلسلة 3.8 هي stable وأن حزمة Windows تتضمن BellSoft 64-bit OpenJDK VM. نُزّل الملف في 2026-07-14 وحُفظ محليًا تحت `tools/weka/downloads/`، وهو Git-ignored. سُجل الحجم وSHA-256 في `tools/weka/source_metadata.json`. لا تعتمد إعادة الإنتاج على Maven artifact أو mirror غير موثق.

نفّذ installer أولًا إلى المسار الافتراضي رغم تمرير custom destination؛ اكتُشف ذلك فورًا. نُسخت التوزيعة نفسها إلى `tools/weka/distribution/` ثم أزيلت النسخة غير المقصودة من `C:\Program Files` بواسطة uninstaller الرسمي. لا يتطلب المشروع الآن system-wide installation ولا تغيير PATH أو administrator settings.

## Java runtime والمترجم

التوزيعة الرسمية تتضمن **BellSoft OpenJDK Runtime 25.0.2+12 LTS**, amd64، وتُستخدم هذه الـ runtime لكل تنفيذ WEKA. لا تتضمن `javac` أو JShell، وفشل Java source-file mode بوضوح لأن module `jdk.compiler` غير موجود.

لتجميع Java bridge القابل للتدقيق استُخدمت حزمة **Liberica Standard JDK 25.0.2+12 Windows amd64 ZIP** المطابقة من BellSoft، وهي الجهة نفسها المزودة للـ VM داخل توزيعة WEKA:

- دليل BellSoft الرسمي: <https://docs.bell-sw.com/liberica-jdk/25.0.2b12/general/install-guide/>
- archive الرسمي: <https://download.bell-sw.com/java/25.0.2+12/bellsoft-jdk25.0.2+12-windows-amd64.zip>

الحزمة portable تحت `tools/weka/jdk/` وGit-ignored، ولم يُعدّل `JAVA_HOME` أو PATH. يستخدم compilation هذا JDK فقط؛ ويستخدم التنفيذ VM المرفق مع WEKA.

## التحقق والإعادة

- WEKA class الفعلية: `weka.associations.FPGrowth`.
- التحقق من version يتم بواسطة `weka.core.Version` ومن `weka.jar` نفسه.
- option help الملتقط من الإصدار الفعلي محفوظ في `weka/results/weka_fpgrowth_help.txt`.
- checksums المحلية، filenames، byte sizes، URLs، retrieval date، ومسارات المشروع النسبية محفوظة في `tools/weka/source_metadata.json`.
- `weka.jar` والتوزيعة وJDK binaries تبقى خارج Git، بينما source metadata والوثائق وJava source تبقى قابلة للتتبع.

لا يحمل installer توقيع Authenticode ظاهرًا في Windows؛ لذلك لا يُستخدم ذلك كدليل هوية. الدليل المسجل هو الرابط الذي تشير إليه صفحة Waikato الرسمية مع الحجم وSHA-256 المحليين، ويجب إعادة التحقق من الملف بعد أي تنزيل جديد.
