#!/usr/bin/env bash
set -o errexit

# Install Flutter SDK
git clone https://github.com/flutter/flutter.git -b stable --depth 1 /opt/flutter

# Add Flutter to PATH
export PATH="/opt/flutter/bin:$PATH"

# Check Flutter installation
flutter --version

# Get dependencies
flutter pub get

# Build Flutter web
flutter build web --release