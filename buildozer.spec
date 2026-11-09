[app]

title = ETİMOKART
package.name = etimokart
package.domain = org.etimokart

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,pdf

version = 1.0.0

# Kararlı sürümler sabitlendi: p4a'nın en yeni (master) hali Python 3.14 çekiyor ve
# Kivy 2.3 ile derleme sırasında hata verebiliyor.
requirements = python3,kivy==2.3.0
p4a.branch = develop

orientation = portrait
fullscreen = 0

android.api = 36
android.minapi = 24
android.ndk = 28c
android.ndk_api = 24
# Test APK'sı için yalnızca 64-bit (güncel telefonların hepsi): derleme süresi yarıya iner.
android.archs = arm64-v8a
android.accept_sdk_license = True

android.release_artifact = aab
android.debug_artifact = apk

android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
