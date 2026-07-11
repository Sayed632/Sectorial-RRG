"""
csv_to_sector_universe.py

Converts PKScreener's own results/Indices/ind_nifty500list.csv (500 NSE
stocks, already tagged with an official Industry column) into the
SECTOR_UNIVERSE dict format used by sector_breadth_treemap.py.

No scraping, no yfinance calls, no Colab needed - the data already exists
in your PKScreener fork.

Usage (run from inside your PKScreener fork):
    python3 csv_to_sector_universe.py \
        --input results/Indices/ind_nifty500list.csv \
        --output sector_universe_generated.py

If you want even broader coverage later, swap --input to
results/Indices/EQUITY_L.csv (all ~2200 listed equities) - but note that
file has NO industry column, so you'd need the yfinance classifier
(build_sector_universe.py) for that one instead. For now, nifty500 gives
you liquid, tradeable names with sector tags already attached - the
better starting point for a swing-trading treemap.
"""
import csv
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/Indices/ind_nifty500list.csv")
    parser.add_argument("--output", default="sector_universe_generated.py")
    parser.add_argument(
        "--min-stocks", type=int, default=5,
        help="Skip sectors with fewer than this many stocks (keeps treemap readable)",
    )
    args = parser.parse_args()

    sector_map = {}
    with open(args.input, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sector = row["Industry"].strip()
            symbol = row["Symbol"].strip() + ".NS"
            sector_map.setdefault(sector, []).append(symbol)

    sector_map = {k: v for k, v in sector_map.items() if len(v) >= args.min_stocks}

    with open(args.output, "w") as f:
        f.write('"""Auto-generated from ind_nifty500list.csv.\n')
        f.write('Paste the SECTOR_UNIVERSE dict below into sector_breadth_treemap.py."""\n\n')
        f.write("SECTOR_UNIVERSE = {\n")
        for sector, tickers in sorted(sector_map.items(), key=lambda x: -len(x[1])):
            f.write(f'    "{sector}": {tickers!r},\n')
        f.write("}\n")

    total = sum(len(v) for v in sector_map.values())
    print(f"Wrote {len(sector_map)} sectors, {total} total stocks, to {args.output}\n")
    for sector, tickers in sorted(sector_map.items(), key=lambda x: -len(x[1])):
        print(f"  {len(tickers):3d}  {sector}")


if __name__ == "__main__":
    main()
