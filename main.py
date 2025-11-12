from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from rapidfuzz import fuzz, process

app = FastAPI()

# Enable CORS — allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load CSV once and normalize
try:
    df = pd.read_csv("EQUITY_L.csv")
    df.columns = df.columns.str.strip().str.upper()
except Exception as e:
    raise RuntimeError(f"Error loading EQUITY_L.csv: {e}")

# Identify correct name column
NAME_COL = None
for candidate in ["NAME OF COMPANY", "NAME", "COMPANY NAME", "COMPANY"]:
    if candidate in df.columns:
        NAME_COL = candidate
        break
if "SYMBOL" not in df.columns or NAME_COL is None:
    raise RuntimeError("EQUITY_L.csv must contain 'SYMBOL' and 'NAME OF COMPANY' columns.")

# Clean columns
df["SYMBOL_STR"] = df["SYMBOL"].astype(str).str.strip()
df["NAME_STR"] = df[NAME_COL].astype(str).str.strip()

@app.get("/search")
def search_symbols(
    q: str = Query(..., description="Search query for symbol or company name"),
    limit: int = Query(15, ge=1, le=100, description="Max number of results")
):
    """
    Fuzzy search NSE symbols and company names.
    Returns the most similar matches (handles typos).
    """
    try:
        query = q.strip().lower()
        if not query:
            raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty.")

        results = []

        # Compute similarity between query and both SYMBOL + NAME
        for _, row in df.iterrows():
            symbol = row["SYMBOL_STR"]
            name = row["NAME_STR"]
            # Measure similarity against both fields separately
            score_symbol = fuzz.ratio(query, symbol.lower())
            score_name = fuzz.partial_ratio(query, name.lower())
            score = max(score_symbol, score_name)
            results.append({"SYMBOL": symbol, "NAME": name, "MATCH_SCORE": round(float(score), 2)})

        # Sort by score descending
        results.sort(key=lambda x: x["MATCH_SCORE"], reverse=True)

        top_results = results[:limit]
        if not top_results:
            raise HTTPException(status_code=404, detail=f"No matches found for query: {q}")

        return {
            "query": q,
            "count": len(top_results),
            "top_result": top_results[0],
            "results": top_results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
