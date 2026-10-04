@echo off
title Copy Google Sites Embed Code
powershell -NoProfile -Command "Get-Content google_sites_embed.html -Raw -Encoding UTF8 | Set-Clipboard"
echo ===============================================================
echo  SUCCESS! The complete Google Sites Embed Code is in your clipboard.
echo ===============================================================
echo  Next Steps:
echo   1. Open https://sites.google.com in your web browser.
echo   2. Create a new site (or edit an existing one).
echo   3. On the right-hand panel, click "Insert" -^> "Embed".
echo   4. Select the "Embed code" tab.
echo   5. Press Ctrl+V to paste the code, then click "Next" -^> "Insert".
echo   6. Drag the corner handles to expand the box to full width/height.
echo   7. Click "Publish" at the top right!
echo ===============================================================
pause
