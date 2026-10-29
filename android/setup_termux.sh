#!/data/data/com.termux/files/usr/bin/bash
# Android Termux Automated Setup Script for Chara Survey Automation
echo "=========================================================="
echo "   चारा टंचाई सर्वेक्षण — Android Termux Setup Script     "
echo "=========================================================="

echo "[1/4] Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo "[2/4] Installing Python, Git, and build tools..."
pkg install -y python git clang libjpeg-turbo libpng make libffi

echo "[3/4] Installing Python dependencies..."
pip install --upgrade pip
pip install flask openpyxl pandas google-genai pymupdf

echo "[4/4] Setup complete!"
echo "To run the app on Android, execute:"
echo "  bash android/run_app.sh"
echo "=========================================================="
