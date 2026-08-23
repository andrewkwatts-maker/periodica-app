[app]

title = Periodica
package.name = periodica
package.domain = com.andrewwatts

source.dir = src/periodica_app
source.include_exts = py,png,jpg,kv,atlas,json,md,ttf
source.include_patterns = config/*.json,kv/*.kv

version = 2.3.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,numpy,periodica

orientation = portrait
fullscreen = 0

# Android
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.permissions =

# Buildozer log level: 2 = verbose
log_level = 2

[buildozer]
warn_on_root = 1
