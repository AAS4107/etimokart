[app]

title = ETİMOKART
package.name = etimokart
package.domain = org.etimokart

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,pdf

version = 1.0.0

requirements = python3,kivy==2.3.1

orientation = portrait
fullscreen = 0

# Google Play, 31 Ağustos 2026'dan beri yeni uygulamalar için API 36 hedefi istiyor.
# Derleme API 36'da hata verirse test için 35'e düşürebilirsin (Play'e yüklemek için 36 gerekir).
android.api = 36
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

# Play Store'a yüklenecek dosya türü: AAB (test için debug'da APK üretilir)
android.release_artifact = aab
android.debug_artifact = apk

android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
