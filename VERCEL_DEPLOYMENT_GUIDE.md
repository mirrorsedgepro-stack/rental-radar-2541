# Vercel Deployment Guide 🚀

The **2541 Rental Radar** app is now deployed and running live on **Vercel** with full zero-configuration Python ASGI serverless backend and global CDN static caching!

---

## 🌐 Live Deployment URL

* **Live Web App**: [**https://temporary-brisk-ridge-hwgke91.vercel.app**](https://temporary-brisk-ridge-hwgke91.vercel.app)
* **API Endpoints**:
  * [Listings API](https://temporary-brisk-ridge-hwgke91.vercel.app/api/listings?max_price=550) (`GET /api/listings?max_price=550`)
  * [Stats API](https://temporary-brisk-ridge-hwgke91.vercel.app/api/stats) (`GET /api/stats`)
  * [Portal Links API](https://temporary-brisk-ridge-hwgke91.vercel.app/api/portal-links) (`GET /api/portal-links`)

---

## 🔑 How to Claim & Keep this Deployment Forever

Because this initial deployment was launched directly from your machine:
1. Open this link in your browser:
   👉 **[https://vercel.com/claim-deployment?code=9799ee08-08e2-4523-9b6d-7f765a38ef26](https://vercel.com/claim-deployment?code=9799ee08-08e2-4523-9b6d-7f765a38ef26)**
2. Sign in or create a free Vercel account (with GitHub, Google, or Email).
3. The deployment will be permanently attached to your Vercel account with a custom `*.vercel.app` domain and free automatic SSL!

---

## 🔄 Deploying Updates

### Option 1: Using the 1-Click Script
Double-click [**`deploy_vercel.bat`**](file:///c:/Users/JED-Tools2/Downloads/Rental/deploy_vercel.bat) in the project folder:
* Choose **Option 2** to log in once with `vercel login` and push updates directly to production.

### Option 2: Deploy from GitHub (Automatic CI/CD)
1. Push this folder to a GitHub repository:
   ```powershell
   git add .
   git commit -m "2541 Rental Radar with Vercel deployment"
   git remote add origin https://github.com/YOUR_USERNAME/rental-2541.git
   git push -u origin main
   ```
2. Go to [https://vercel.com/new](https://vercel.com/new) and import your `rental-2541` repository.
3. Click **Deploy**. Vercel will automatically re-deploy every time you push a commit!

---

## 📁 How the Vercel Architecture Works

* **Static Frontend**: Located in `public/` (and `static/`). Vercel serves `index.html`, `app.js`, and `style.css` globally via its Edge CDN with sub-50ms latency.
* **Serverless Backend**: Located in `api/index.py` which mounts the FastAPI application. Vercel automatically runs requests to `/api/*` as Python Serverless Functions.
* **Pre-seeded Database**: The SQLite database (`rentals_2541.db`) is copied to `/tmp/rentals_2541.db` in serverless instances, providing persistent and fast local read/write queries.
