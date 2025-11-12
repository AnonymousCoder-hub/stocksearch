# Symbol Search API (with CORS)

A simple FastAPI application that searches for NSE symbols and company names from `EQUITY_L.csv`.  
Fully deployable on **Vercel** and accessible from **any frontend** thanks to CORS.

---

## 🚀 Deployment on Vercel

1. Push these files to a GitHub repository:
   - `main.py`
   - `requirements.txt`
   - `readme.md`
   - `EQUITY_L.csv`

2. Go to [vercel.com](https://vercel.com/) and create a new project linked to your repository.

3. Configure:
   - **Framework preset:** `Other`
   - **Build command:**  
     ```
     uvicorn main:app --host 0.0.0.0 --port $PORT
     ```
   - **Output directory:** *(leave blank)*

4. Click **Deploy**.

Vercel will build and host your API. You’ll get a public URL like: