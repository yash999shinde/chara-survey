@echo off
title Chara Survey Automation Server
echo ========================================================
echo    चारा टंचाई सर्वेक्षण (Chara Survey Automation)
echo ========================================================
echo.
echo Python पर्यावरण तपासत आहे...
if exist .venv\Scripts\python.exe (
    set PY=.venv\Scripts\python.exe
) else (
    set PY=python
)

echo Server सुरू होत आहे...
echo कॉम्प्युटरवर: http://127.0.0.1:5000
echo मोबाईलवर (Same Wi-Fi): http://0.0.0.0:5000
echo.
%PY% -m app.app
pause
