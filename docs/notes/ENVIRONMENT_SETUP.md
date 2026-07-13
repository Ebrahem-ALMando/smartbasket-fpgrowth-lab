# إعداد بيئة المشروع (Environment Setup)

## البيئة المؤكدة

تم التحقق من البيئة بتاريخ 13 يوليو 2026. يعمل المشروع على Python 3.11.9 بنسخة 64-bit ومعمارية AMD64. أعاد `platform.platform()` القيمة `Windows-10-10.0.26100-SP0`، وهي القيمة التي يعلنها Python عن منصة Windows الحالية.

- **إصدار Python العام:** `Python 3.11.9`.
- **المفسر العام:** `%LOCALAPPDATA%\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe`.
- **إصدار pip العام وقت الفحص:** `pip 25.1.1`.
- **موقع البيئة الافتراضية:** `.venv` داخل جذر المشروع.
- **مفسر المشروع:** `.venv\Scripts\python.exe`.
- **إصدار Python داخل البيئة:** `Python 3.11.9`، 64-bit، AMD64.
- **أداة الحزم داخل البيئة:** `pip 26.1.2` بعد الترقية.

لم تكن البيئة الافتراضية مفعلة في جلسة الفحص، ولذلك لا يعتمد المشروع على استمرار حالة التفعيل بين الأوامر. يشير اختلاف `sys.prefix` عن `sys.base_prefix` إلى أن `.venv\Scripts\python.exe` مفسر افتراضي مستقل عن بيئة المستخدم العامة.

## إنشاء البيئة الافتراضية

كانت `.venv` موجودة قبل بدء Phase 2. أظهر `pyvenv.cfg` أنها أُنشئت من Python 3.11.9 باستخدام وحدة `venv`، ثم أثبت الفحص أن المفسر يقع داخل المشروع ويعمل بصورة صحيحة؛ لذلك لم تُحذف البيئة ولم يُعَد إنشاؤها.

الأمر النسبي المكافئ المسجل لإنشائها هو:

```powershell
python -m venv .venv
```

يُستخدم هذا الأمر فقط عند إعداد نسخة جديدة من المشروع أو بعد إزالة بيئة تالفة عمداً. لا ينبغي تشغيله فوق بيئة سليمة بلا حاجة.

## الأوامر المنفذة لتثبيت الاعتماديات

نُفذت الأوامر التالية من جذر المشروع، باستخدام مفسر `.venv` مباشرةً ومن دون `pip --user` أو تثبيت عام:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

ثم سُجلت البيئة المحلولة وفُحص اتساقها:

```powershell
.\.venv\Scripts\python.exe -m pip freeze --all | Set-Content -Encoding utf8 requirements-resolved.txt
.\.venv\Scripts\python.exe -m pip check
```

أعاد `pip check` الرسالة `No broken requirements found.` ونجح استيراد جميع الاعتماديات المباشرة وواجهات `fpgrowth` و`apriori` و`association_rules`.

## تفعيل البيئة في PowerShell

ملف التفعيل موجود وتم التحقق منه. يمكن تفعيل البيئة في جلسة PowerShell الحالية بالأمر:

```powershell
.\.venv\Scripts\Activate.ps1
```

بعد التفعيل، يجب أن يشير الأمر التالي إلى مسار داخل `.venv`:

```powershell
python -c "import sys; print(sys.executable)"
```

إذا منعت سياسة PowerShell تشغيل ملف التفعيل، يمكن الاستغناء عن التفعيل كلياً واستخدام المفسر مباشرةً. لا توصي هذه الوثيقة بتغيير سياسة التنفيذ على مستوى النظام من أجل المشروع.

## الاستخدام من دون تفعيل

هذه هي الطريقة الأكثر وضوحاً في الأوامر الآلية لأنها تمنع الخلط بين Python العام ومفسر المشروع:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
.\.venv\Scripts\python.exe -m pip check
```

يجب أن يظهر المسار النسبي `.venv\Scripts\python.exe` في مخرجات التحقق.

## اختيار المفسر في VS Code

1. افتح لوحة الأوامر باستخدام `Ctrl + Shift + P`.
2. اختر `Python: Select Interpreter`.
3. اختر `.venv\Scripts\python.exe` من جذر المشروع.
4. افتح طرفية جديدة وتحقق من `python -c "import sys; print(sys.executable)"`.

اختيار المفسر الصحيح يعالج عادةً تحذيرات الاستيراد أو رسالة عدم العثور على الحزم عندما يكون VS Code ما زال يستخدم Python العام.

## تشغيل JupyterLab مستقبلاً

تم التحقق من توفر أمر JupyterLab ومساعدته، لكن لم يبدأ خادم ولم يُنشأ Notebook في Phase 2. عند بدء مرحلة الدفاتر يمكن تشغيله من جذر المشروع:

```powershell
.\.venv\Scripts\python.exe -m jupyter lab
```

الإصدارات المؤكدة هي JupyterLab 4.6.1 وNotebook 7.6.0 وipywidgets 8.1.8.

## التحقق من المفسر الصحيح

يمكن تنفيذ الفحص التالي قبل أي تجربة:

```powershell
.\.venv\Scripts\python.exe -c "import sys, platform, struct; print(sys.version); print(sys.executable); print(platform.platform()); print(platform.machine()); print(struct.calcsize('P') * 8)"
```

المؤشرات المطلوبة هي Python 3.11.9، ومسار ينتهي بـ `.venv\Scripts\python.exe`، ومعمارية AMD64، وعمق 64-bit.

## غياب مشغل py

الأمر `py` غير متاح، لكن ذلك لا يمنع المشروع. يعمل `python` الخاص بتثبيت Microsoft Store، وتعمل البيئة من خلال `.venv\Scripts\python.exe`. جميع الأوامر الموثقة تستخدم `python` أو مفسر البيئة مباشرةً ولا تعتمد على Python Launcher.

## requirements.txt وrequirements-resolved.txt

- يحتوي `requirements.txt` على النطاقات المقصودة للاعتماديات المباشرة، بما يسمح بحل إصدارات متوافقة عند إعداد البيئة.
- يحتوي `requirements-resolved.txt` على لقطة `pip freeze --all` الكاملة للإصدارات المباشرة والانتقالية التي نجحت فعلياً في هذه البيئة.

لا يحل الملف المجمد محل ملف النطاقات. لإعادة إنتاج البيئة الحالية بأعلى دقة يمكن استخدام الملف المحلول بعد مراجعة توافق النظام، بينما يبقى `requirements.txt` مصدر سياسة الاعتماديات.

## خطوات الاستعادة عند تلف .venv

1. أغلق Jupyter وVS Code terminals التي تستخدم البيئة.
2. احتفظ بـ `requirements.txt` و`requirements-resolved.txt` ولا تعدّل البيانات أو المخرجات.
3. أعد تسمية البيئة التالفة أو احذفها يدوياً فقط بعد التأكد من أن المسار هو `.venv` داخل المشروع.
4. أنشئ البيئة مجدداً باستخدام `python -m venv .venv`.
5. استخدم مفسر البيئة مباشرةً لترقية أدوات الحزم ثم التثبيت من `requirements.txt`.
6. نفّذ `pip check` واختبارات الاستيراد، ثم أعد توليد `requirements-resolved.txt` إذا تغيّر الحل.
7. أعد اختيار `.venv\Scripts\python.exe` في VS Code.

لا ينبغي نسخ `.venv` بين أجهزة أو إضافتها إلى Git؛ الملف `.gitignore` يستبعدها بالفعل.

## تحديث اعتماديات Phase 3

أضيف `pytest>=8,<10` إلى `requirements.txt` بوصفه اعتمادية تطوير خفيفة ومباشرة لتشغيل اختبارات خط تجهيز البيانات. ثُبت الإصدار المحلول 9.1.1 داخل `.venv` فقط، ثم أُعيد توليد `requirements-resolved.txt` ونجح `pip check`. لم تُضف اعتمادية بيانات كبيرة.
