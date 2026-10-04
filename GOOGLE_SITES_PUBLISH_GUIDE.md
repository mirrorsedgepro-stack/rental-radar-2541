# How to Publish to Google Sites (sites.google.com) 🌐

You can publish the **2541 Rental Radar** app to Google Sites for free in under 2 minutes.

---

## ⚡ Option 1: Fast Direct Embed (Recommended)

This method embeds the complete, self-contained interactive app directly into your Google Site without needing any hosting accounts or servers.

### Step 1: Copy the Embed Code
- **Double-click** [`copy_to_clipboard.bat`](file:///c:/Users/JED-Tools2/Downloads/Rental/copy_to_clipboard.bat) in this folder.
- *Alternatively, open [`google_sites_embed.html`](file:///c:/Users/JED-Tools2/Downloads/Rental/google_sites_embed.html), select all (`Ctrl+A`), and copy (`Ctrl+C`).*

### Step 2: Open Google Sites
1. Open your browser and go to **[https://sites.google.com](https://sites.google.com)**.
2. Sign in with your Google account.
3. Click **Blank** (or choose any template) to create a new site.
4. Name your site (e.g. `Nowra & Bomaderry Rentals`).

### Step 3: Embed the App
1. In the right-hand sidebar under **Insert**, click on **Embed** (the `< >` icon).
2. A popup window will appear with two tabs: *By URL* and *Embed code*.
3. Click the **Embed code** tab.
4. Paste the code from your clipboard (`Ctrl+V`).
5. Click **Next**, review the live interactive preview, and click **Insert**.

### Step 4: Adjust Layout & Publish
1. Hover over the newly inserted block on your page.
2. Click and drag the **blue corner handles** to expand the widget to **full width** and **full height** so the map, cards, and tabs have plenty of room to display.
3. At the top right of the Google Sites editor, click the purple/blue **Publish** button.
4. Choose a web address suffix (e.g. `2541-rentals` or `nowra-rentals`).
5. Click **Publish**!
6. Your app is now live at:
   `https://sites.google.com/view/your-web-address`

---

## ☁️ Option 2: Publish via Google Cloud Run (Full 24/7 Python Backend)

If you want the Python backend and auto-scraper running continuously on Google Cloud:

1. **Install the Google Cloud CLI**:
   Download and install from: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
2. **Login to Google Cloud**:
   ```powershell
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. **Deploy with 1 command**:
   ```powershell
   gcloud run deploy rental-2541 --source . --region australia-southeast1 --allow-unauthenticated
   ```
4. Google Cloud will build the container with the provided [`Dockerfile`](file:///c:/Users/JED-Tools2/Downloads/Rental/Dockerfile) and give you a public HTTPS URL (e.g. `https://rental-2541-xxxx-ts.a.run.app`).
5. In Google Sites, you can simply click **Insert > Embed > By URL** and paste your Cloud Run URL!

---

## 🔄 Updating Data on Your Google Site

When you want to refresh the listings on your Google Site:
1. Run `python scraper.py` locally to fetch the latest properties.
2. Run `python build_google_sites_embed.py` to bake the newest listings into `google_sites_embed.html`.
3. Double-click `copy_to_clipboard.bat`, go to your Google Site, click the embed edit icon (pencil), replace the code with `Ctrl+V`, and click **Publish**!
