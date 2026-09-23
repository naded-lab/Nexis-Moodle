# Nexis Model — الهيكل الأولي

هاد أول هيكل مشروع لتطبيق Nexis، مبني بـ Kotlin + Jetpack Compose، وجاهز يشتغل عبر GitHub Actions بدون الحاجة لـ Android Studio.

## شو موجود هلق
- `app/` — مشروع Android أساسي، شاشة Compose وحيدة (`MainActivity.kt`) تعرض "Nexis" بلون العلامة التجارية (#0F6E56)، هدفها بس التأكد إن خط الإنتاج (Termux → GitHub → Actions → APK) شغال.
- `app/.../models/AiModelAdapter.kt` — الواجهة الموحّدة (interface) يلي أي مزوّد AI (Claude, GPT, Gemini, KiMi...) رح يطبّقها. هاي بنية التصميم الشامل يلي حكينا عنها — التنفيذ الفعلي (استدعاء API حقيقي) لسه TODO.
- `.github/workflows/build-apk.yml` — يبني APK تلقائيًا عند كل push لفرع `main`، وينزّله كـ artifact.

## خطوات التشغيل من Termux
```bash
# 1. انسخ هاد المجلد لمستودع Git جديد (أو ادمجه بمستودع موجود)
git init
git add .
git commit -m "Initial Nexis project skeleton"

# 2. اربطه بمستودع GitHub جديد وارفعه
git remote add origin <رابط-المستودع-تبعك>
git branch -M main
git push -u origin main
```

بعد الـ push، روح لتبويب **Actions** بمستودع GitHub — لازم يبلش build تلقائيًا، وبعد ما يخلص، بتلاقي `nexis-debug-apk` جاهز للتحميل من صفحة الـ workflow run.

## الخطوة الجاية (بعد ما تتأكد إن الـ build شغال)
1. ربط `ClaudeAdapter` بـ Anthropic API فعليًا (أول نموذج حقيقي).
2. شاشة إعدادات بسيطة لإدخال مفتاح Claude وتخزينه عبر `EncryptedSharedPreferences` (Android Keystore).
3. أول شاشة محادثة فعلية لمساعد Coding.


## Local model
Nexis Model keeps the GGUF model outside the APK. Use Settings → النموذج المحلي to select an existing Qwen2.5-0.5B-Instruct Q4_K_M `.gguf` file, or open the embedded direct download link.

Official direct model URL:
https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf
