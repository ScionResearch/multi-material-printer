#!/bin/bash
#
# Scion Multi-Material Printer Controller
# Build and Run Script
#
# This script compiles the Qt application and launches it
# Usage: ./build_and_run.sh
#

set -e  # Exit on any error

echo "🔨 Building Scion Multi-Material Unit Controller..."
echo "=================================================="

# Navigate to the GUI source directory
cd src/gui

# Clean any previous builds
echo "🧹 Cleaning previous build..."
make clean 2>/dev/null || true
rm -f Makefile 2>/dev/null || true

# Generate Makefile from .pro file
echo "⚙️  Generating Makefile..."
qmake ScionMMUController.pro

# Build the application
echo "🔨 Compiling application..."
make -j$(nproc)

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "✅ Build completed successfully!"
    echo ""
    
    # Navigate back to project root
    cd ../..
    
    # Check if the executable exists
    if [ -f "build/ScionMMUController" ]; then
        echo "🚀 Launching Scion Multi-Material Unit Controller..."
        echo "=================================================="
        
        # Make sure it's executable
        chmod +x build/ScionMMUController
        
        # Run the application
        ./build/ScionMMUController
    else
        echo "❌ Error: Executable not found in build/ directory"
        echo "Expected: build/ScionMMUController"
        exit 1
    fi
else
    echo "❌ Build failed!"
    exit 1
fi