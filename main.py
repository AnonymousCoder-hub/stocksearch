# main.py
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

# Load CSV once at startup and normalize columns
try:
    df = pd.read_csv("EQUITY_L.csv")
    df.columns = df.columns.str.strip().str.upper()
except Exception as e:
    raise RuntimeError(f"Error loading EQUITY_L.csv: {e}")

# Attempt to find a suitable name column (common variants)
NAME_COL = None
for candidate in ["NAME OF COMPANY", "NAME", "COMPANY NAME", "COMPANY"]:
    if candidate in df.columns:
        NAME_COL = candidate
        break

if "SYMBOL" not in df.columns or NAME_COL is None:
    raise RuntimeError("EQUITY_L.csv must contain a SYMBOL column and a company name column (e.g. 'NAME OF COMPANY').")

# Prepare combined strings and mapping for fast fuzzy search
df["SYMBOL_STR"] = df["SYMBOL"].astype(str).str.strip()
df["NAME_STR"] = df[NAME_COL].astype(str).str.strip()
df["COMBINED"] = (df["SYMBOL_STR"] + " " + df["NAME_STR"]).str.lower()

# Build choices list and mapping index -> (symbol, name)
choices = df["COMBINED"].tolist()
index_to_meta = df[["SYMBOL_STR", "NAME_STR"]].to_dict(orient="index")

@app.get("/search")
def search_symbols(q: str = Query(..., description="Search query for symbol or company name"),
                   limit: int = Query(15, ge=1, le=100, description="Max number of results to return")):
    """
    Fuzzy search NSE symbols/company names with ranking.
    Returns best matches (highest similarity first), works for typos.
    """
    try:
        query = q.strip().lower()
        if not query:
            raise HTTPException(status_code=400, detail="Query parameter 'q' must be non-empty.")

        # Use rapidfuzz.process.extract for fast top-N fuzzy matching
        # returns list of tuples: (choice, score, index)
        extracted = process.extract(
            query,
            choices,
            scorer=fuzz.token_sort_ratio,
            limit=limit
        )

        # Build results mapping back to SYMBOL and NAME
        results = []
        for choice_text, score, idx in extracted:
            meta = index_to_meta.get(idx)
            if meta:
                results.append({
                    "SYMBOL": meta["SYMBOL_STR"],
                    "NAME": meta["NAME_STR"],
                    "MATCH_SCORE": round(float(score), 2)
                })

        if not results:
            raise HTTPException(status_code=404, detail=f"No matches found for query: {q}")

        return {
            "query": q,
            "count": len(results),
            "top_result": results[0],
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        # return a 500 with readable message
        raise HTTPException(status_code=500, detail=str(e))
