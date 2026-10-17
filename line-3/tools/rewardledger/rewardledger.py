#!/usr/bin/env python3
"""Create a deterministic, unsigned review ledger from an allocation report."""
import argparse, csv, hashlib, json, pathlib, sys

FIELDS = ("id", "address", "weight_fraction", "units", "amount", "rounding_unit_awarded")

def main(argv=None):
    p = argparse.ArgumentParser(description="Turn a verified allocation report into a stable review CSV")
    p.add_argument("report", help="JSON allocation report")
    p.add_argument("--output", help="new CSV path; stdout when omitted")
    args = p.parse_args(argv)
    path = pathlib.Path(args.report)
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("allocations")
    if not isinstance(rows, list) or not rows: raise ValueError("report must contain a non-empty allocations array")
    seen, out = set(), []
    for row in rows:
        needed = ("id", "weight_fraction", "units", "amount", "rounding_unit_awarded")
        if not isinstance(row, dict) or not all(k in row for k in needed): raise ValueError("each allocation needs exact review fields")
        if not isinstance(row["id"], str) or row["id"] in seen: raise ValueError("contributor IDs must be unique strings")
        seen.add(row["id"])
        out.append([row["id"], row.get("address", ""), row["weight_fraction"], row["units"], row["amount"], str(row["rounding_unit_awarded"]).lower()])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    stream = sys.stdout if not args.output else open(args.output, "x", newline="", encoding="utf-8")
    try:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["report_sha256", digest]); writer.writerow(FIELDS); writer.writerows(out)
    finally:
        if args.output: stream.close()
    print(json.dumps({"rows": len(out), "report_sha256": digest, "output": args.output or "stdout"}, sort_keys=True), file=sys.stderr)

if __name__ == "__main__":
    try: main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("rewardledger: " + str(exc), file=sys.stderr); raise SystemExit(2)
