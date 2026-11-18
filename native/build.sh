#!/bin/sh
# Build the replacement InControlNative plugin used by the Bluetooth DualShock 4 mode.
# Universal binary: the game loads the x86_64 slice.
set -e
cd "$(dirname "$0")"
clang -O2 -Wall -fvisibility=hidden -mmacosx-version-min=10.13 -bundle -arch x86_64 -arch arm64 \
    -o InControlNative InControlNative.c -framework IOKit -framework CoreFoundation
echo "Built native/InControlNative"
