"""Compare what the simulator injected with what Silver quarantined (proof that cleaning works).

    python scripts/check_quarantine_vs_log.py --log logs/change_log_aws.jsonl --out docs/evidence/s2-silver-quarantine-check.md

The original Olist data also contains a few bad rows, so the rule is: quarantined >= injected.
Exit code 1 if Silver quarantined FEWER rows than the simulator injected for any problem.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sources"))

# simulator problem -> (quarantine source_table, reason_code)
EXPECTED = {
    "negative_price": ("order_items", "invalid_price"),
    "orphan_order": ("orders", "orphan_customer"),
    "impossible_timeline": ("orders", "impossible_timeline"),
    "bad_review_score": ("order_reviews", "invalid_score"),
    "duplicate_review": ("order_reviews", "duplicate_review"),
}


def injected_counts(log_path):
    entries = [json.loads(line) for line in Path(log_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    deleted = {e["key"].get("order_id") for e in entries if e["type"] == "deleted_order"}
    # An order deleted later cannot be quarantined: it no longer exists.
    deleted_reviews = {e["detail"].get("review_id") for e in entries if e["type"] == "deleted_review"} - {None}
    # A row deleted later at the source cannot be quarantined: it no longer exists.
    return Counter(e["type"] for e in entries
                if e["type"] in EXPECTED
                and e["key"].get("order_id") not in deleted
                and e["key"].get("review_id") not in deleted_reviews)


def compare(injected, quarantined):
    """quarantined: {(source_table, reason_code): count}"""
    rows = []
    for problem, (table, reason) in EXPECTED.items():
        got = quarantined.get((table, reason), 0)
        rows.append((problem, injected.get(problem, 0), f"{table}/{reason}", got, got >= injected.get(problem, 0)))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--log", required=True)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    from klarity_snowflake import connect
    conn = connect(database="SILVER", schema="CORE")
    cur = conn.cursor()
    cur.execute("select source_table, reason_code, count(*) from SLV_QUARANTINE group by 1, 2")
    quarantined = {(a, b): n for a, b, n in cur.fetchall()}
    conn.close()
    rows = compare(injected_counts(args.log), quarantined)
    lines = ["| injected problem | injected | quarantined as | quarantined | result |", "|---|---|---|---|---|"]
    lines += [f"| {p} | {i} | {q} | {g} | {'PASS' if ok else 'FAIL'} |" for p, i, q, g, ok in rows]
    text = "\n".join(lines)
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
    return 0 if all(r[4] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
