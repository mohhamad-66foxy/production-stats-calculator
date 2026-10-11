[app]
# Application info
title = Production Statistics Calculator
package.name = prodstats
package.domain = org.production
source.dir = .
source.include_exts = py,png,jpg,kv,atlas

# Version and requirements
version = 1.0
requirements = python3,kivy,pillow

# App config
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Android build settings
android.api = 31
android.minapi = 21
android.ndk = 25.1.8937393
android.archs = arm64-v8a
android.private_storage = True

# Additional build settings
p4a.branch = stable

[buildozer]
log_level = 2
