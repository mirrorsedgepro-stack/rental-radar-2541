# Vercel Deployment Guide 🚀

The **Radar Realty Australia** app is now deployed and running live on **Vercel** with full zero-configuration Python ASGI serverless backend and global CDN static caching!

---

## 🌐 Live Deployment URL

* **Live Web App**: [**https://temporary-snappy-slate-6w21ecf.vercel.app**](https://temporary-snappy-slate-6w21ecf.vercel.app)
* **API Endpoints**:
  * [Listings API](https://temporary-snappy-slate-6w21ecf.vercel.app/api/listings?listing_type=rent) (`GET /api/listings?listing_type=rent`)
  * [Stats API](https://temporary-snappy-slate-6w21ecf.vercel.app/api/stats) (`GET /api/stats`)
  * [Portal Links API](https://temporary-snappy-slate-6w21ecf.vercel.app/api/portal-links) (`GET /api/portal-links`)

---

## 🔑 How to Claim & Keep this Deployment Forever

1. Open this link in your browser to permanently attach it to your Vercel account:
   👉 **[https://vercel.com/claim-deployment?code=535312eb-00c1-4990-8b13-8a6dce241f1f](https://vercel.com/claim-deployment?code=535312eb-00c1-4990-8b13-8a6dce241f1f)**
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
   git commit -m "Radar Realty Australia with Vercel deployment"
   git remote add origin https://github.com/YOUR_USERNAME/rental-radar.git
   git push -u origin main
   ```
2. Go to [https://vercel.com/new](https://vercel.com/new) and import your repository.
3. Click **Deploy**. Vercel will automatically re-deploy every time you push a commit!

---

## 📁 How the Vercel Architecture Works

* **Static Frontend**: Located in `public/` (and `static/`). Vercel serves `index.html`, `app.js`, and `style.css` globally via its Edge CDN with sub-50ms latency.
* **Serverless Backend**: Located in `api/index.py` which mounts the FastAPI application. Vercel automatically runs requests to `/api/*` as Python Serverless Functions.
* **Pre-seeded Database**: The SQLite database (`australia_properties.db`) is copied to `/tmp/australia_properties.db` in serverless instances, providing persistent and fast local read/write queries.
