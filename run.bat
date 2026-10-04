@echo off
title Radar Realty Australia - Property Radar
echo ===================================================
echo   RADAR REALTY AUSTRALIA - PROPERTY & RENTAL RADAR
echo ===================================================
python start.py
if errorlevel 1 (
    echo.
    echo An error occurred running python start.py.
    pause
)
