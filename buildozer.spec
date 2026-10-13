[app]

# (str) Title of your application
title = Cabo

# (str) Package name
package.name = cabo

# (str) Package domain (needed for android packaging)
package.domain = org.cabo.game

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,ttf,wav,ogg

# (list) Source files to exclude
source.exclude_exts = spec

# (list) List of directory to exclude
source.exclude_dirs = bin, .buildozer, .git, .github

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# Pygame-CE is the modern, actively-maintained SDL2 backend supported on Android
requirements = python3,pygame-ce

# (str) Supported orientations
# Valid options are: landscape, portrait, portrait-reverse, landscape-reverse
orientation = landscape

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (list) Permissions
android.permissions = 

# (int) Target Android API, should be as high as allowed by Google Play
android.api = 34

# (int) Minimum API your APK will support
android.minapi = 21

# (int) Android NDK API to use
android.ndk_api = 21

# (bool) If True, then automatically accept all OEM SDK licenses
android.accept_sdk_license = True

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

# (bool) Allow backup
android.allow_backup = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug when '-v' is given)
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
