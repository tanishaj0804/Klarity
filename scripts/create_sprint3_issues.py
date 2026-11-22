"""Create the Sprint 3 milestone, labels and issues, and add them to the project board.

    python scripts/create_sprint3_issues.py --dry-run     # print what would happen
    python scripts/create_sprint3_issues.py               # do it (needs: gh auth login)
    python scripts/create_sprint3_issues.py --add-to-board   # also add to the Project board

Adding to the board needs the project scope once:  gh auth refresh -s project
Safe to re-run: issues whose title already exists are skipped.
"""
import argparse
import json
import subprocess
import sys

REPO = "tanishaj0804/Klarity"
OWNER = "tanishaj0804"
PROJECT_NUMBER = "1"
MILESTONE = "v0.3 Gold ready"
DUE = "2026-11-23T18:00:00Z"
LABELS = {"sprint-3": "1D76DB", "dbt": "FF694B", "silver": "6C7A89", "gold": "A07A05", "fivetran": "5319E7"}

# id, title, points, labels, why, acceptance criteria
STORIES = [
    ("S3-01", "Silver layer in dbt: staging, clean tables, quarantine", 3, ["dbt", "silver"],
     "Raw Bronze is cleaned once, and bad rows are kept out and counted.",
     ["Staging views and slv_ tables build", "Quarantine table with reason codes", "39 tests pass (dbt build: 60 of 60)"]),
    ("S3-02", "Gold core: dimensions and facts", 3, ["dbt", "gold"],
     "The star schema the dashboard reads.",
     ["dim_customer, dim_product, dim_seller, dim_date", "fct_orders and fct_order_items", "Three KPIs hand-checked against Silver"]),
    ("S3-03", "Customer history (SCD2) and point-in-time join", 4, ["dbt", "gold"],
     "An order must show the address the customer had when they bought, not today's.",
     ["Snapshot snap_customers on city, state, zip", "int_order_customer_pit returns exactly one row per order", "dbt unit test on moved customer passes",
      "Evidence: a customer with two versions and their old and new orders"]),
    ("S3-04", "Incremental fact with merge, reprocess window and delete handling", 4, ["dbt", "gold"],
     "Production loading pattern. Oracle is a full refresh, so rows are rewritten and removed.",
     ["fct_order_items uses merge with a composite unique key", "Open orders and a 30 day window are reprocessed", "Rows deleted or quarantined upstream are removed",
      "Test: fact equals Silver after an incremental run"]),
    ("S3-05", "RFM scoring and cohort retention", 3, ["dbt", "gold"],
     "Business logic across the whole customer history.",
     ["mart_customer_rfm with NTILE scores and segments", "mart_cohort_retention matrix with LAG", "Both pass their tests"]),
    ("S3-06", "Delivery performance and anomaly flags", 2, ["dbt", "gold"],
     "Shows how late delivery affects reviews, and flags unusual days.",
     ["mart_late_delivery_impact", "mart_daily_orders_anomaly with 7-day rolling z-score"]),
    ("S3-07", "Macros and custom generic tests", 2, ["dbt", "gold"],
     "Remove repetition and show metaprogramming.",
     ["pivot_sum and delete_missing_rows macros", "not_negative and valid_timeline generic tests", "Quarantine rules built from one list (macro)"]),
    ("S3-08", "Governance: contracts, unit tests, source freshness, exposures", 2, ["dbt", "gold"],
     "Engineering maturity, not just SQL.",
     ["Model contract enforced on at least one Gold model", "Unit tests pass", "Source freshness configured", "Exposure for the dashboard"]),
    ("S3-09", "Prove inserts, updates and deletes reach Gold (carries S2-09)", 2, ["dbt", "fivetran"],
     "End to end proof with the simulator, and the live-change demo.",
     ["Run daily_changes.py, sync, load Oracle, dbt build", "Change log entries found in Bronze, Silver and Gold", "Evidence saved"]),
]


def gh(args, dry, capture=False):
    cmd = ["gh"] + args
    if dry:
        print("DRY:", " ".join(a if " " not in a else repr(a) for a in cmd))
        return ""
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode:
        print("gh failed:", " ".join(cmd[:4]), "\n", res.stderr.strip())
        raise SystemExit(1)
    return res.stdout


def body(sid, points, why, criteria):
    lines = [f"**Story {sid}** | **Points: {points}** | Sprint 3 (21 to 23 Nov 2026)", "", "**Why**", why, "",
             "**Acceptance criteria**"] + [f"- [ ] {c}" for c in criteria]
    lines += ["", "**Definition of done**", "- [ ] Evidence saved in `docs/evidence/`", "- [ ] PR merged, CI green",
              "- [ ] No secrets committed"]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--add-to-board", action="store_true")
    a = ap.parse_args(argv)
    d = a.dry_run

    for name, color in LABELS.items():
        gh(["label", "create", name, "--color", color, "--repo", REPO, "--force"], d)
    existing_ms = "" if d else gh(["api", f"repos/{REPO}/milestones?state=all", "--jq", ".[].title"], d)
    if MILESTONE not in existing_ms.splitlines():
        gh(["api", f"repos/{REPO}/milestones", "-f", f"title={MILESTONE}", "-f", f"due_on={DUE}",
            "-f", "description=Sprint 3: Silver and Gold with dbt, 21 to 23 Nov 2026"], d)
    have = set()
    if not d:
        out = gh(["issue", "list", "--repo", REPO, "--state", "all", "--limit", "300", "--json", "title"], d)
        have = {i["title"] for i in json.loads(out)}

    total = 0
    for sid, title, pts, labels, why, crit in STORIES:
        full = f"{sid}: {title}"
        total += pts
        if full in have:
            print("exists, skipped:", full)
            continue
        args = ["issue", "create", "--repo", REPO, "--title", full, "--body", body(sid, pts, why, crit),
                "--milestone", MILESTONE]
        for lb in ["sprint-3"] + labels:
            args += ["--label", lb]
        url = gh(args, d).strip()
        if a.add_to_board and not d:
            gh(["project", "item-add", PROJECT_NUMBER, "--owner", OWNER, "--url", url], d)
        elif a.add_to_board:
            gh(["project", "item-add", PROJECT_NUMBER, "--owner", OWNER, "--url", "<issue url>"], d)
        print("created:" if not d else "would create:", full)
    print(f"Total points: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
