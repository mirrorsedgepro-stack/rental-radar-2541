# 2541 Rental Radar 🏠

A tailored, real-time application for tracking and securing housing rentals in **postcode 2541** (Nowra, Bomaderry, North Nowra, South Nowra, West Nowra, Bangalee, Terara) under **$550 per week**.

---

## 🌟 Key Features

1. **Live Rental Aggregator & Tracker**:
   - Automatically crawls and syncs active rental listings across all suburbs in NSW postcode 2541.
   - Strictly tracks properties priced at or below **$550/week** (with a flexible budget slider from $300 to $650).
   - Flags newly listed properties with a glowing **NEW** badge so you can apply first.

2. **Interactive 2541 Map View (Leaflet)**:
   - Visualizes all properties with color-coded price badges:
     - 🟢 **Green**: Under $450/wk (Bargain entry)
     - 🔵 **Blue**: $450 – $500/wk (Great value)
     - 🟠 **Amber**: $501 – $550/wk (Budget limit)
   - Built-in landmark toggles:
     - 🚆 **Bomaderry Railway Station** (direct train line to Wollongong and Sydney Central)
     - 🏥 **Shoalhaven District Memorial Hospital**
     - 🛍️ **Stockland Nowra Shopping Centre**
     - 🎓 **University of Wollongong (UOW) Shoalhaven Campus**
     - 🚌 **Stewart Place Bus Interchange**

3. **Application & Inspection Pipeline (Kanban)**:
   - Track each property through 5 stages:
     - 🔍 **Discovered / Watching**
     - ⭐ **Shortlisted**
     - 📅 **Inspection Booked**
     - 📝 **Application Submitted**
     - 🎉 **Offered / Leased**
   - Save personal notes, ratings (1–5 stars), and inspection observations.

4. **1-Click Open House Calendar (.ics) & Printable Run Sheet**:
   - Download `.ics` files for upcoming inspections to add directly to Google Calendar, Apple Calendar, or Outlook.
   - Click **Run Sheet** for a clean, print-friendly schedule of open homes for weekend house hunting.

5. **Super Search Launchpad**:
   - 1-click pre-filtered search buttons configured for **postcode 2541 under $550/wk** across:
     - **Realestate.com.au**
     - **Domain.com.au**
     - **Rent.com.au**
     - **Allhomes.com.au**
     - **Homely.com.au**
     - **Gumtree Australia** (private rentals)
     - **Flatmates.com.au** (granny flats, studios)
     - **Local Shoalhaven Agencies**: Ray White Nowra, Integrity Real Estate, LJ Hooker Nowra, Raine & Horne Nowra.

6. **Tenant Toolkit & Affordability Calculator**:
   - **NSW Bond & Move-In Cost Calculator**: Computes 4-week NSW rental bond, 2-week upfront rent, monthly costs, and annual commitments.
   - **30% Affordability Check**: Calculates minimum gross household income required to avoid rental stress.
   - **Shoalhaven Renter Bio Generator**: Custom cover letter generator ready to paste into 2Apply or Ignite.
   - **100-Point ID Checklist**: Verification checklist so your documents are ready within 10 minutes of inspection.

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
├── scraper.py            # Live crawler for 2541 listings with address & coordinate parser
├── database.py           # SQLite database layer (rentals_2541.db)
├── start.py              # Launcher script (starts server & opens browser)
├── run.bat               # Windows 1-click batch launcher
├── requirements.txt      # Python dependencies
├── static/
│   ├── index.html        # Modern responsive frontend interface
│   ├── app.js            # Frontend logic (Map, Kanban, Filters, Calculator)
│   └── style.css         # Styling, animations, print stylesheet
└── README.md             # Documentation
```
