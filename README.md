# Radar Realty Australia 🏠🏡

A tailored, real-time application for discovering, tracking, and securing properties to **Rent & Buy** across all of **Australia** (NSW, VIC, QLD, WA, SA, ACT, and TAS).

---

## 🌟 Key Features

1. **Nationwide Property Aggregator & Tracker**:
   - Seamlessly toggle between **For Rent** and **For Sale** modes.
   - Automatically crawls and syncs active properties across capital cities and regional communities nationwide.
   - Budget selectors with flexible sliders for weekly rent or home purchase budgets.
   - Glowing **NEW** badge highlights freshly listed properties so you can apply or inspect first.

2. **Interactive Australia Property Map (Leaflet)**:
   - Visualizes properties nationwide with color-coded badges:
     - 🟢 **Green**: Value rentals (under $550/wk)
     - 🔵 **Blue**: Mid-range rentals ($551–$850/wk)
     - 🟠 **Amber**: Premium rentals
     - 🟣 **Purple**: Houses & properties for sale
   - Quick Zoom buttons for Sydney, Melbourne, Brisbane, Perth, Adelaide, Hobart, and Canberra.

3. **Application & Inspection Pipeline (Kanban)**:
   - Track each property through 5 stages:
     - 🔍 **Discovered / Watching**
     - ⭐ **Shortlisted**
     - 📅 **Inspection Booked**
     - 📝 **Application Submitted**
     - 🎉 **Offered / Leased / Purchased**
   - Save personal notes, ratings (1–5 stars), and inspection observations with private cookie isolation.

4. **1-Click Open House Calendar (.ics) & Printable Run Sheet**:
   - Download `.ics` files for upcoming inspections to add directly to Google Calendar, Apple Calendar, or Outlook.
   - Click **Run Sheet** for a clean, print-friendly schedule of open homes for weekend house hunting.

5. **Super Search Launchpad**:
   - 1-click pre-filtered search buttons across Australia's leading property portals:
     - **Realestate.com.au**
     - **Domain.com.au**
     - **Rent.com.au**
     - **Allhomes.com.au**
     - **Homely.com.au**
     - **Soho Real Estate**
     - **Ray White Group**

6. **Financial Toolkit & Affordability Calculators**:
   - **Rental Bond & Move-In Cost Calculator**: Computes 4-week rental bond, upfront rent, and annual commitments.
   - **Mortgage Repayment Calculator**: Computes estimated monthly repayments, interest, and loan terms for purchase properties.
   - **30% Affordability Check**: Calculates minimum gross household income required to avoid housing stress.
   - **Renter Bio Generator & 100-Point ID Checklist**: Ready-to-copy profile descriptions for rental applications.

7. **Background Alerts & Notifications**:
   - Background periodic worker checks for new listings every 30 minutes (configurable).
   - Audio chime and browser desktop notifications when new deals appear.
   - Webhook support (send instant alerts to a Discord or Slack channel).

8. **Add Custom Rentals**:
   - Spot a "For Lease" sign or private listing on Facebook Marketplace? Click **+ Add Rental** to integrate it into your map, pipeline, and notes.

---

## 🚀 How to Run

### Method 1: Double-Click Launcher (Windows)
Double-click `run.bat` in this folder. It will launch the server and automatically open the application in your default web browser at `http://127.0.0.1:8000`.

### Method 2: Command Line
```powershell
python start.py
```
Or:
```powershell
python server.py
```
Then visit `http://127.0.0.1:8000` in your browser.

---

## 📁 Project Structure

```
Rental/
├── server.py             # FastAPI backend with REST endpoints & background scheduler
├── scraper.py            # Live crawler with address & coordinate parser
├── database.py           # SQLite database layer (australia_properties.db)
├── start.py              # Launcher script (starts server & opens browser)
├── run.bat               # Windows 1-click batch launcher
├── requirements.txt      # Python dependencies
├── static/
│   ├── index.html        # Modern responsive frontend interface
│   ├── app.js            # Frontend logic (Map, Kanban, Filters, Calculator)
│   └── style.css         # Styling, animations, print stylesheet
└── README.md             # Documentation
```
