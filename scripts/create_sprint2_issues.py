"""Create the Sprint 2 milestone, labels and issues, and add them to the project board.

    python scripts/create_sprint2_issues.py --dry-run     # print what would happen
    python scripts/create_sprint2_issues.py               # do it (needs: gh auth login)
    python scripts/create_sprint2_issues.py --add-to-board   # also add to the Project board

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
MILESTONE = "v0.2 Bronze ready"
DUE = "2026-11-27T18:00:00Z"
LABELS = {"sprint-2": "1D76DB", "fivetran": "5319E7", "snowflake": "0E8A16", "security": "B60205"}

# id, title, points, labels, why, acceptance criteria
STORIES = [
    ("S2-01", "Snowflake account, warehouse, resource monitor, BRONZE/SILVER/GOLD databases", 2, ["snowflake"],
     "The trial clock starts at sign-up, so this is day 1 of the sprint. A resource monitor protects the credits.",
     ["Account created; sign-up date noted in the README", "XS warehouse, auto-suspend 60 s",
      "Resource monitor with notify at 50 percent and suspend at 90 percent",
      "Databases BRONZE, SILVER, GOLD exist; script saved in infra/snowflake/"]),
    ("S2-02", "Snowflake roles: LOADER, TRANSFORMER, REPORTER", 2, ["snowflake", "security"],
     "Least privilege: Fivetran may only write Bronze; dbt reads Bronze and writes Silver and Gold; the dashboard only reads Gold.",
     ["Three roles with grants as a script", "Each role proven by one allowed and one refused statement (evidence file)"]),
    ("S2-03", "Read-only source users on Oracle, MySQL and PostgreSQL", 1, ["security", "fivetran"],
     "Fivetran must not be able to change the sources.",
     ["One read-only user per database", "Proven: SELECT works, INSERT is refused", "Passwords only in .env files and the password manager"]),
    ("S2-04", "Fivetran: PostgreSQL to Snowflake Bronze", 3, ["fivetran"],
     "Easiest source first, to learn the Fivetran flow. wal_level=logical is already set (ADR 0005).",
     ["Connector syncs products, sellers, category_translation, geolocation", "Row counts in Bronze equal the source",
      "Sync frequency chosen and recorded"]),
    ("S2-05", "Fivetran: MySQL to Snowflake Bronze", 2, ["fivetran"],
     "Second source. Needs binary logging for log-based sync (check the Fivetran guide).",
     ["Connector syncs customers and order_reviews", "Row counts in Bronze equal the source"]),
    ("S2-06", "Fivetran: Oracle to Snowflake Bronze (with fallback decision)", 5, ["fivetran"],
     "Highest risk: Fivetran's Oracle connector may need a paid plan and may not support Oracle XE (setup guide checked 7 Nov).",
     ["Day 1 of this story: confirm plan and XE support with the Fivetran trial", "If supported: orders, order_items, order_payments in Bronze",
      "If not: write an ADR for the fallback (for example a Python loader) and get mentor approval before building it"]),
    ("S2-07", "Network: firewall allows only Fivetran and my IPs", 1, ["security"],
     "Fivetran runs in the cloud, so it must reach the EC2 ports. Nothing may be open to 0.0.0.0/0.",
     ["Security group rules for the Fivetran IP list of the chosen region plus my IPs", "aws_host.py status shows no 0.0.0.0/0"]),
    ("S2-08", "Reconciliation: source row counts against Bronze", 3, ["snowflake"],
     "The idea of verify_load.py, now across systems. Proves Fivetran copied everything.",
     ["SQL or script compares count and key sums per table", "Result table saved in docs/evidence/", "All tables match after the baseline sync"]),
    ("S2-09", "Prove inserts, updates and deletes reach Bronze", 3, ["fivetran"],
     "This is why the simulator exists.",
     ["Run daily_changes.py, sync, then check the change log entries against Bronze", "Deleted rows are visible as soft deletes (record the flag name)"]),
    ("S2-10", "Schema drift test: add a column at the source", 2, ["fivetran"],
     "Real sources change. Bronze must keep working.",
     ["Column added in one source", "Fivetran adds it to Bronze; result and any problem recorded"]),
    ("S2-11", "Cost log and weekly cost check", 1, ["snowflake"],
     "A habit: credits and AWS cost every week.",
     ["docs/cost-log.md with date, Snowflake credits used, Fivetran rows used, AWS credits left"]),
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
    lines = [f"**Story {sid}** | **Points: {points}** | Sprint 2 (16 to 27 Nov 2026)", "", "**Why**", why, "",
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
            "-f", "description=Sprint 2: Bronze with Fivetran, 16 to 27 Nov 2026"], d)
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
        for lb in ["sprint-2"] + labels:
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
