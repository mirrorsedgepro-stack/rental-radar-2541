@echo off
title Deploy Radar Realty Australia to Vercel
echo ===============================================================
echo   RADAR REALTY AUSTRALIA - VERCEL DEPLOYMENT TOOL
echo ===============================================================
echo.
set "PATH=C:\Users\JED-Tools2\AppData\Local\Python\pythoncore-3.14-64\Scripts;%PATH%"

echo 1. Deploy anonymously / temporary
echo 2. Login to Vercel and deploy to your account (Permanent Production)
echo.
set /p choice="Select an option (1 or 2): "

if "%choice%"=="1" (
    echo.
    echo Deploying temporary preview...
    npx.cmd vercel deploy --temporary
) else (
    echo.
    echo Logging in to Vercel...
    npx.cmd vercel login
    echo.
    echo Deploying to production...
    npx.cmd vercel --prod
)

echo.
echo ===============================================================
pause
