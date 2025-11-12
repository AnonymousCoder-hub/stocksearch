from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from rapidfuzz import fuzz, process

app = FastAPI()

# Enable CORS — accessible from anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load CSV once
try:
    df = pd.read_csv("EQUITY_L.csv")
    df.columns = df.columns.str.strip().str.upper()
except Exception as e:
    raise RuntimeError(f"Error loading EQUITY_L.csv: {e}")

@app.get("/search")
def search_symbols(q: str = Query(..., description="Search query for symbol or company name")):
    """
    Search NSE symbols or company names with fuzzy ranking.
    Returns best matches even for typos or approximate queries.
    """
    try:
        if "SYMBOL" not in df.columns or "NAME OF COMPANY" not in df.columns:
            raise HTTPException(status_code=500, detail="EQUITY_L.csv must contain SYMBOL and NAME OF COMPANY columns")

        query = q.strip().lower()

        df["SYMBOL_LOWER"] = df["SYMBOL"].str.lower()
        df["NAME_LOWER"] = df["NAME OF COMPANY"].str.lower()

        # Combine symbol and name for better matching context
        df["COMBINED"] = df["SYMBOL_LOWER"] + " " + df["NAME_LOWER"]

        # Use RapidFuzz to calculate similarity score
        scored = []
        for _, row in df.iterrows():
            score = fuzz.token_sort_ratio(query, row["COMBINED"])
            scored.append((row["SYMBOL"], row["NAME OF COMPANY"], score))

        # Sort by highest similarity score
        scored.sort(key=lambda x: x[2], reverse=True)

        # Pick top 15 results (you can adjust)
        results = [{"SYMBOL": s, "NAME OF COMPANY": n, "MATCH_SCORE": round(score, 2)} for s, n, score in scored[:15]]

        if not results:
            raise HTTPException(status_code=404, detail=f"No matches found for query: {q}")

        return {
            "query": q,
            "top_result": results[0],
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
