import sys
from pathlib import Path
import requests
from collections import Counter

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import SETTINGS

def fetch(params):
    r = requests.get(f"{SETTINGS.GAMMA_HOST}/markets", params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def summarize(markets, label):
    c_restricted = Counter()
    c_closed = Counter()
    c_archived = Counter()
    c_active = Counter()
    has_clob = 0
    for m in markets:
        c_restricted[bool(m.get("restricted", False))] += 1
        c_closed[bool(m.get("closed", False))] += 1
        c_archived[bool(m.get("archived", False))] += 1
        c_active[bool(m.get("active", False))] += 1
        if m.get("clobTokenIds"):
            has_clob += 1

    print(f"\n=== {label} ===")
    print("count:", len(markets))
    print("active:", dict(c_active))
    print("closed:", dict(c_closed))
    print("archived:", dict(c_archived))
    print("restricted:", dict(c_restricted))
    print("has clobTokenIds:", has_clob)

    print("\nExamples (first 5):")
    for m in markets[:5]:
        print({
            "id": m.get("id"),
            "slug": m.get("slug"),
            "active": m.get("active"),
            "closed": m.get("closed"),
            "archived": m.get("archived"),
            "restricted": m.get("restricted"),
            "volume24hr": m.get("volume24hr"),
            "clobTokenIds_present": bool(m.get("clobTokenIds")),
        })

def main():
    # Query A: as open as possible, ordered by volume24hr
    params_a = {"limit": 50, "offset": 0, "order": "volume24hr", "ascending": False}
    mk_a = fetch(params_a)
    summarize(mk_a, "A) /markets ordered by volume24hr (no filters)")

    # Query B: explicitly closed=false (open)
    params_b = {"limit": 50, "offset": 0, "order": "volume24hr", "ascending": False, "closed": False}
    mk_b = fetch(params_b)
    summarize(mk_b, "B) /markets closed=false")

    # Query C: explicitly restricted=false
    params_c = {"limit": 50, "offset": 0, "order": "volume24hr", "ascending": False, "closed": False, "restricted": False}
    mk_c = fetch(params_c)
    summarize(mk_c, "C) /markets closed=false & restricted=false")

if __name__ == "__main__":
    main()
