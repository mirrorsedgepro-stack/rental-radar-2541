import os
import sys
import time
import webbrowser
import threading
import uvicorn

def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:8000"
    print(f"\n[+] Opening browser at {url} ...")
    webbrowser.open(url)

if __name__ == "__main__":
    print("=" * 65)
    print("   2541 RENTAL RADAR - Nowra & Bomaderry Housing Rentals under $550")
    print("=" * 65)
    print(" • Postcode 2541: Nowra, Bomaderry, North Nowra, South Nowra, West Nowra")
    print(" • Live Tracker, Interactive Map, Application Kanban & Super Search")
    print(" • Server running at: http://127.0.0.1:8000")
    print(" • Press Ctrl+C in this window to stop the server.")
    print("=" * 65 + "\n")
    
    # Launch browser in a background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start server
    uvicorn.run("server:app", host="127.0.0.1", port=8000, log_level="info")
