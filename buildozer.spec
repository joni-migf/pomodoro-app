[app]
title = Nuyo Pomodoro Timer
package.name = nuoyopomodoro
package.domain = org.example.pomodoro

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,mp3

version = 0.1
requirements = python3,kivy==2.3.0,plyer

[buildozer]
log_level = 2
warn_on_root = 1

[app]
android.permissions = INTERNET,VIBRATE,RECEIVE_BOOT_COMPLETED,WAKE_LOCK
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.gradle_dependencies = 

presplash.filename = %(source.dir)s/presplash.png  # Add image later if wanted
icon.filename = %(source.dir)s/icon.png  # Add app icon later
orientation = portrait
fullscreen = 0
android.archs = arm64-v8a, armeabi-v7a
