#!/usr/bin/env bash
set -e

# Install Flutter in the writable project directory
git clone https://github.com/flutter/flutter.git \
  -b stable --depth 1 .flutter-sdk

# Add Flutter to PATH
export PATH="$PWD/.flutter-sdk/bin:$PATH"

# Verify installation
flutter --version

# Download dependencies
flutter pub get

# Build Flutter web
flutter build web --release
