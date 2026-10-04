@echo off
title 2541 Rental Radar
echo ===================================================
echo   2541 RENTAL RADAR (Nowra & Bomaderry ^< $550/wk)
echo ===================================================
python start.py
if errorlevel 1 (
    echo.
    echo An error occurred running python start.py.
    pause
)
