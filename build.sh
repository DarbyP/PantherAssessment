#!/bin/bash

echo "Building PantherAssess for macOS..."
echo

# Check if pyinstaller is installed
if ! pip show pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Build the application
pyinstaller build_mac.spec

if [ $? -ne 0 ]; then
    echo
    echo "Build failed!"
    exit 1
fi

echo
echo "Build complete!"
echo "Application location: dist/PantherAssess.app"
echo
echo "You can now distribute the PantherAssess.app file"
echo "To create a DMG for easier distribution, you can use:"
echo "  hdiutil create -volname PantherAssess -srcfolder dist/PantherAssess.app -ov -format UDZO PantherAssess.dmg"
