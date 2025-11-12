from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI()

# Enable CORS — allows requests from any domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Load CSV file once at startup
try:
    df = pd.read_csv("EQUITY_L.csv")
    df.columns = df.columns.str.strip().str.upper()  # Normalize column names
except Exception as e:
    raise RuntimeError(f"Error loading EQUITY_L.csv: {e}")

@app.get("/search")
def search_symbols(q: str = Query(..., description="Search query for symbol or company name")):
    """
    Search for matching stock symbols or company names from EQUITY_L.csv.
    Prioritizes exact and starts-with matches, then partial matches.
    """
    try:
        query = q.strip().lower()

        if "SYMBOL" not in df.columns or "NAME OF COMPANY" not in df.columns:
            raise HTTPException(status_code=500, detail="EQUITY_L.csv must have columns: SYMBOL, NAME OF COMPANY")

        df["SYMBOL_LOWER"] = df["SYMBOL"].str.lower()
        df["NAME_LOWER"] = df["NAME OF COMPANY"].str.lower()

        # Step 1: Exact matches
        exact_matches = df[(df["SYMBOL_LOWER"] == query) | (df["NAME_LOWER"] == query)]

        # Step 2: Starts-with matches (only if no exact match)
        starts_with = df[
            (df["SYMBOL_LOWER"].str.startswith(query)) | (df["NAME_LOWER"].str.startswith(query))
        ] if exact_matches.empty else pd.DataFrame()

        # Step 3: Partial matches (only if no exact or starts-with match)
        partial_matches = df[
            (df["SYMBOL_LOWER"].str.contains(query)) | (df["NAME_LOWER"].str.contains(query))
        ] if exact_matches.empty and starts_with.empty else pd.DataFrame()

        combined = pd.concat([exact_matches, starts_with, partial_matches]).drop_duplicates(subset=["SYMBOL"])

        if combined.empty:
            raise HTTPException(status_code=404, detail=f"No matches found for query: {q}")

        results = combined[["SYMBOL", "NAME OF COMPANY"]].to_dict(orient="records")

        return {"query": q, "count": len(results), "results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))