# S1-10 evidence: daily change simulator

`sources/daily_changes.py` simulates one day of business activity in the three source databases. It adds new orders, moves open orders along their life cycle (with reviews for delivered ones), changes some customer addresses, injects a known set of data-quality problems, and writes every change to a change log (`logs/change_log.jsonl`) that serves as an answer key.


one clean day (`--dirty 0 --now 2026-11-01T09:00:00 --seed 1`), then seven days with injected problems (`foreach ($d in 2..8) { python sources/daily_changes.py --now "2026-11-0${d}T09:00:00" --seed $d }`).

`python sources/verify_load.py --changes logs/change_log.jsonl` result: [paste the last line, for example "NNN passed, 0 failed."]. Every logged change was found in the databases.

## Change log summary

| Change type | Count | Where |
| --- | --- | --- |
| new_order | 400 | Oracle, MySQL |
| status_update | 240 | Oracle |
| address_change | 39 | MySQL |
| new_review | 3 | MySQL |
| mixed_case | 14 | MySQL |
| negative_price | 14 | Oracle |
| orphan_order | 14 | Oracle (customer missing in MySQL) |
| order_without_items | 14 | Oracle |
| null_estimated_date | 14 | Oracle |
| impossible_timeline | 14 | Oracle |
| duplicate_review | 14 | MySQL |
| bad_review_score | 14 | MySQL |
| deleted_review | 7 | MySQL |
| deleted_order | 7 | Oracle |

## Reading the numbers

- 8 runs of 50 new orders give 400 orders, and 8 runs of 30 status updates give 240.
- 14 of each injected problem comes from 7 dirty runs times 2 per run. The first run was clean on purpose.
- Address changes are 39 rather than 40 because one random move picked the same city and was skipped.
- Only 3 reviews were created. A review is written when an order reaches "delivered", and an order needs five steps to get there. After 8 simulated days, only the earliest orders finished the journey. More runs will add reviews.
- The DBeaver queries from the plan found the injected rows (negative prices, impossible dates, mixed-case cities, duplicate reviews, out-of-range scores).

## What this proves

The sources change over time and contain a known, countable set of data-quality problems. Profiling (S1-11) and the dbt tests in Sprint 3 can be checked against these counts, and Sprint 2 can use the same simulator to prove that inserts, updates and deletes reach Bronze.
