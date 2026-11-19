[app]
title = Etimokart
package.name = etimokart
package.domain = org.etimokart
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0
requirements = python3,kivy==2.3.0,certifi,openssl
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 36
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.release_artifact = aab
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
