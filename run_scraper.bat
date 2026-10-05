@echo off
title Radar Realty Australia - Multi-Portal Property Scraper
setlocal enabledelayedexpansion

echo =====================================================================
echo   RADAR REALTY AUSTRALIA - PROPERTY & RENTAL MULTI-PORTAL SCRAPER
echo   Portals: Realestate.com.au, Domain, Rent.com.au, Homely, Soho
echo =====================================================================
echo.

set "PATH=C:\Users\JED-Tools2\AppData\Local\Python\pythoncore-3.14-64\Scripts;C:\Users\JED-Tools2\AppData\Local\Python\pythoncore-3.14-64;%PATH%"

echo Select an option:
echo   1. Quick Scrape: Australia-wide Rentals (Under $550/wk default)
echo   2. Suburb / City Scrape: Enter a specific city (e.g. Sydney, Melbourne, Brisbane)
echo   3. Properties for Sale: Scrape houses & apartments for purchase
echo   4. Custom Search: Specify location, mode, and max budget
echo   5. Exit
echo.

set /p choice="Enter choice (1-5, default 1): "

if "%choice%"=="" set choice=1
if "%choice%"=="5" exit /b 0

if "%choice%"=="1" (
    echo.
    echo [*] Starting Australia-wide rental scrape across all portals...
    uv run python scraper.py --suburb australia --mode rent
    goto :done
)

if "%choice%"=="2" (
    echo.
    set /p city="Enter suburb or city name (e.g. Sydney, Melbourne, Brisbane, Perth, Adelaide): "
    echo [*] Scraping rentals in !city!...
    uv run python scraper.py --suburb "!city!" --mode rent
    goto :done
)

if "%choice%"=="3" (
    echo.
    echo [*] Scraping properties for sale nationwide...
    uv run python scraper.py --suburb australia --mode sale
    goto :done
)

if "%choice%"=="4" (
    echo.
    set /p target_loc="Enter location (or press Enter for Australia): "
    if "!target_loc!"=="" set target_loc=australia
    
    set /p target_mode="Enter mode (rent or sale, default rent): "
    if "!target_mode!"=="" set target_mode=rent
    
    set /p target_price="Enter max budget cap (e.g. 650 for rent or 1200000 for sale): "
    
    if "!target_price!"=="" (
        uv run python scraper.py --suburb "!target_loc!" --mode "!target_mode!"
    ) else (
        uv run python scraper.py --suburb "!target_loc!" --mode "!target_mode!" --max-price !target_price!
    )
    goto :done
)

:done
echo.
echo =====================================================================
echo   Crawl complete! All properties saved to australia_properties.db.
echo =====================================================================
echo.
pause
