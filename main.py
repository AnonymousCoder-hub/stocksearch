from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from rapidfuzz import fuzz

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load & clean the CSV
try:
    df = pd.read_csv("EQUITY_L.csv")
    df.columns = df.columns.str.strip().str.upper()
except Exception as e:
    raise RuntimeError(f"Error loading EQUITY_L.csv: {e}")

# Detect company name column
NAME_COL = None
for candidate in ["NAME OF COMPANY", "NAME", "COMPANY NAME", "COMPANY"]:
    if candidate in df.columns:
        NAME_COL = candidate
        break

if "SYMBOL" not in df.columns or NAME_COL is None:
    raise RuntimeError("EQUITY_L.csv must contain 'SYMBOL' and a company name column.")

# Prepare columns
df["SYMBOL_STR"] = df["SYMBOL"].astype(str).str.strip()
df["NAME_STR"] = df[NAME_COL].astype(str).str.strip()
df["_sym_l"] = df["SYMBOL_STR"].str.lower()
df["_name_l"] = df["NAME_STR"].str.lower()


def compute_symbol_first_score(query: str, sym: str, name: str):
    """
    Prioritize matches to the symbol field.
    Symbol matches get higher weight.
    """
    # Basic fuzzy ratios
    score_sym_token = fuzz.token_set_ratio(query, sym)
    score_sym_partial = fuzz.partial_ratio(query, sym)
    score_name_token = fuzz.token_set_ratio(query, name)
    score_name_partial = fuzz.partial_ratio(query, name)

    # Combine: symbol is much more important
    score = (
        (score_sym_token * 1.4)
        + (score_sym_partial * 1.2)
        + (score_name_token * 0.6)
        + (score_name_partial * 0.5)
    ) / 3.7  # Normalize to ~0-100

    # Boost exact or startswith matches in SYMBOL
    if sym == query:
        score += 25
    elif sym.startswith(query):
        score += 15

    # Boost startswith matches in NAME slightly
    if name.startswith(query):
        score += 8

    # Clamp to 100
    if score > 100:
        score = 100
    return round(float(score), 2)


@app.get("/search")
def search_symbols(
    q: str = Query(..., description="Search query for symbol or company name"),
    limit: int = Query(15, ge=1, le=100, description="Max results to return"),
):
    """
    Search symbols with symbol-first ranking and fuzzy fallback.
    """
    try:
        query_raw = q.strip()
        query = query_raw.lower()
        if not query:
            raise HTTPException(status_code=400, detail="Query 'q' cannot be empty.")

        results = []
        for _, row in df.iterrows():
            sym_l = row["_sym_l"]
            name_l = row["_name_l"]
            score = compute_symbol_first_score(query, sym_l, name_l)
            results.append(
                {
                    "SYMBOL": row["SYMBOL_STR"],
                    "NAME": row["NAME_STR"],
                    "MATCH_SCORE": score,
                }
            )

        # Sort: by score → symbol startswith → shorter symbol → alphabetically
        results.sort(
            key=lambda r: (
                r["MATCH_SCORE"],
                r["SYMBOL"].lower().startswith(query),
                -len(r["SYMBOL"]),
                r["SYMBOL"].lower(),
            ),
            reverse=True,
        )

        top = results[:limit]
        if not top:
            raise HTTPException(status_code=404, detail=f"No matches found for '{q}'")

        return {
            "query": query_raw,
            "count": len(top),
            "top_result": top[0],
            "results": top,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
