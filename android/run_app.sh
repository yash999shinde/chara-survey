#!/data/data/com.termux/files/usr/bin/bash
# Android Termux Launcher Script
echo "=========================================================="
echo "   चारा टंचाई सर्वेक्षण — सुरू होत आहे (Android Local)..."
echo "=========================================================="

export FLASK_HOST="0.0.0.0"
export FLASK_PORT=5000

# Get local Android IP if available
IP=$(ip addr show wlan0 2>/dev/null | grep -o 'inet [0-9.]*' | cut -d' ' -f2)
if [ -z "$IP" ]; then
    IP="localhost"
fi

echo ">> ॲप सुरू झाले आहे!"
echo ">> तुमच्या मोबाईल ब्राउझरमध्ये उघडा: http://localhost:5000"
if [ "$IP" != "localhost" ]; then
    echo ">> इतर मोबाईलवरून उघडण्यासाठी: http://$IP:5000"
fi
echo "=========================================================="

python -m app.app
