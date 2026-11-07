"""Simulate a day of business activity in the three source databases (story S1-10).

What one run does:
  1. NEW ORDERS     new customers, orders, items and payments (Oracle + MySQL)
  2. STATUS UPDATES open orders move one step along their life cycle, delivered orders
                    may get a review (late deliveries get worse scores)
  3. ADDRESS CHANGES a few customers move house (update in place)
  4. DIRTY DATA     a small, known number of data-quality problems are injected
  5. CHANGE LOG     every change is written to logs/change_log.jsonl: the answer key

Usage (repo root, venv active):
    python sources/daily_changes.py                       # normal day, with dirty data
    python sources/daily_changes.py --dirty 0             # clean day, no injected problems
    python sources/daily_changes.py --now 2026-11-01      # pretend it is another day
    python sources/daily_changes.py --seed 7              # same seed, same changes

Run it only AFTER load_olist.py and verify_load.py have passed (the baseline).
"""
import argparse
import hashlib
import json
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, insert, select, update

from klarity_db import REPO, T, get_engine

SIM_EPOCH = datetime(2025, 1, 1)  # simulator orders are newer than the 2016-2018 Olist data
FLOW = {"created": "approved", "approved": "invoiced", "invoiced": "processing",
        "processing": "shipped", "shipped": "delivered"}
PAY_TYPES = ["credit_card", "boleto", "voucher", "debit_card"]
PAY_WEIGHTS = [74, 19, 5, 2]
COMMENTS = ["Produto chegou antes do prazo", "Entrega atrasou muito", "Gostei, recomendo",
            "Produto diferente do anunciado", "Tudo certo"]


class Sim:
    def __init__(self, args):
        self.rng = random.Random(args.seed)
        self.now = args.now
        self.args = args
        self.run_id = f"{self.now:%Y%m%dT%H%M%S}-{args.seed}"
        self.log = []
        self.counter = 0
        self.ora, self.my, self.pg = get_engine("oracle"), get_engine("mysql"), get_engine("postgres")

    # ---- helpers -------------------------------------------------------------
    def hexid(self):
        """A 32-character id that is unique per run (run id + counter), and repeatable."""
        self.counter += 1
        return hashlib.md5(f"{self.run_id}:{self.counter}".encode()).hexdigest()

    def note(self, kind, system, table, key, **detail):
        self.log.append({"run_id": self.run_id, "ts": self.now.isoformat(), "type": kind,
                         "system": system, "table": table, "key": key, "detail": detail})

    def load_pools(self):
        with self.my.connect() as c:
            self.customers = [tuple(r) for r in c.execute(select(
                T["customers"].c.customer_id, T["customers"].c.customer_unique_id,
                T["customers"].c.customer_zip_code_prefix, T["customers"].c.customer_city,
                T["customers"].c.customer_state))]
        with self.pg.connect() as c:
            self.products = [r[0] for r in c.execute(select(T["products"].c.product_id))]
            self.sellers = [r[0] for r in c.execute(select(T["sellers"].c.seller_id))]
        if not (self.customers and self.products and self.sellers):
            raise SystemExit("The databases are empty. Run load_olist.py first.")

    # ---- 1. new orders -------------------------------------------------------
    def new_orders(self):
        rng, now = self.rng, self.now
        orders, items, pays, custs = [], [], [], []
        for _ in range(self.args.orders):
            oid, cid = self.hexid(), self.hexid()
            _, uid, zip_, city, state = rng.choice(self.customers)
            if rng.random() > 0.3:  # 70 percent are new people, 30 percent come back
                uid = self.hexid()
            purchase = now - timedelta(minutes=rng.randint(1, 600))
            status = rng.choice(["created", "approved"])
            orders.append({
                "order_id": oid, "customer_id": cid, "order_status": status,
                "order_purchase_timestamp": purchase,
                "order_approved_at": purchase + timedelta(minutes=rng.randint(5, 90)) if status == "approved" else None,
                "order_delivered_carrier_date": None, "order_delivered_customer_date": None,
                "order_estimated_delivery_date": (purchase + timedelta(days=rng.randint(7, 30))).replace(hour=0, minute=0, second=0, microsecond=0)})
            custs.append({"customer_id": cid, "customer_unique_id": uid, "customer_zip_code_prefix": zip_,
                          "customer_city": city, "customer_state": state})
            total = 0
            for n in range(1, rng.randint(1, 3) + 1):
                price = round(min(2000, max(5, rng.lognormvariate(4.3, 0.8))), 2)
                freight = round(rng.uniform(5, 45), 2)
                total += price + freight
                items.append({"order_id": oid, "order_item_id": n, "product_id": rng.choice(self.products),
                              "seller_id": rng.choice(self.sellers),
                              "shipping_limit_date": purchase + timedelta(days=3),
                              "price": price, "freight_value": freight})
            ptype = rng.choices(PAY_TYPES, PAY_WEIGHTS)[0]
            pays.append({"order_id": oid, "payment_sequential": 1, "payment_type": ptype,
                         "payment_installments": rng.randint(1, 10) if ptype == "credit_card" else 1,
                         "payment_value": round(total, 2)})
        self.inject_into_new_orders(orders, items, pays, custs)
        with self.my.begin() as c:
            if custs:
                c.execute(insert(T["customers"]), custs)
        with self.ora.begin() as c:
            if orders:
                c.execute(insert(T["orders"]), orders)
            if items:
                c.execute(insert(T["order_items"]), items)
            if pays:
                c.execute(insert(T["order_payments"]), pays)
        for o in orders:
            self.note("new_order", "oracle", "orders", {"order_id": o["order_id"]}, status=o["order_status"])
        self.new_order_ids = [o["order_id"] for o in orders]

    # ---- 4a. dirt that lives inside the new rows -----------------------------
    def inject_into_new_orders(self, orders, items, pays, custs):
        k = self.args.dirty
        if not k or not orders:
            return
        wanted = ["mixed_case", "negative_price", "orphan_order", "order_without_items",
                  "null_estimated_date", "impossible_timeline"]
        slots = self.rng.sample(range(len(orders)), min(len(orders), k * len(wanted)))
        plan = [(wanted[n % len(wanted)], idx) for n, idx in enumerate(slots)]
        drop_items, drop_custs = set(), set()
        for kind, idx in plan:
            o, cu = orders[idx], custs[idx]
            oid = o["order_id"]
            if kind == "mixed_case":
                cu["customer_city"], cu["customer_state"] = cu["customer_city"].upper(), cu["customer_state"].lower()
                self.note(kind, "mysql", "customers", {"customer_id": cu["customer_id"]},
                          city=cu["customer_city"], state=cu["customer_state"])
            elif kind == "negative_price":
                first = next(x for x in items if x["order_id"] == oid)
                first["price"] = -abs(first["price"])
                self.note(kind, "oracle", "order_items", {"order_id": oid, "order_item_id": 1}, price=first["price"])
            elif kind == "orphan_order":
                drop_custs.add(cu["customer_id"])
                self.note(kind, "oracle", "orders", {"order_id": oid}, customer_id=cu["customer_id"])
            elif kind == "order_without_items":
                drop_items.add(oid)
                self.note(kind, "oracle", "orders", {"order_id": oid})
            elif kind == "null_estimated_date":
                o["order_estimated_delivery_date"] = None
                self.note(kind, "oracle", "orders", {"order_id": oid})
            elif kind == "impossible_timeline":
                p = o["order_purchase_timestamp"]
                o.update(order_status="delivered", order_approved_at=p + timedelta(hours=1),
                         order_delivered_carrier_date=p + timedelta(days=1),
                         order_delivered_customer_date=p - timedelta(days=2))
                self.note(kind, "oracle", "orders", {"order_id": oid})
        items[:] = [x for x in items if x["order_id"] not in drop_items]
        pays[:] = [x for x in pays if x["order_id"] not in drop_items]
        custs[:] = [x for x in custs if x["customer_id"] not in drop_custs]

    # ---- 2. status updates and reviews ---------------------------------------
    def status_updates(self):
        rng, now = self.rng, self.now
        o = T["orders"]
        with self.ora.connect() as c:
            rows = c.execute(select(o.c.order_id, o.c.order_status, o.c.order_estimated_delivery_date).where(
                o.c.order_status.in_(list(FLOW)), o.c.order_purchase_timestamp >= SIM_EPOCH,
                o.c.order_purchase_timestamp < now)).all()
        rows = rng.sample(rows, min(self.args.updates, len(rows)))
        reviews = []
        with self.ora.begin() as c:
            for oid, status, estimated in rows:
                new = "canceled" if status != "shipped" and rng.random() < 0.03 else FLOW[status]
                values = {"order_status": new}
                if new == "approved":
                    values["order_approved_at"] = now
                elif new == "shipped":
                    values["order_delivered_carrier_date"] = now
                elif new == "delivered":
                    values["order_delivered_customer_date"] = now
                c.execute(update(o).where(o.c.order_id == oid).values(**values))
                self.note("status_update", "oracle", "orders", {"order_id": oid}, old_status=status, new_status=new)
                if new == "delivered" and rng.random() < 0.7:
                    score = rng.choices([5, 4, 3, 2, 1], [57, 19, 8, 3, 13])[0]
                    if estimated is not None and now > estimated and rng.random() < 0.7:
                        score = rng.choice([1, 2, 3])  # late delivery, unhappy customer
                    message = rng.choice(COMMENTS) if rng.random() < 0.2 else None
                    reviews.append({"review_id": self.hexid(), "order_id": oid, "review_score": score,
                                    "review_comment_title": None, "review_comment_message": message,
                                    "review_creation_date": now, "review_answer_timestamp": now + timedelta(hours=rng.randint(1, 48))})
        if reviews:
            with self.my.begin() as c:
                c.execute(insert(T["order_reviews"]), reviews)
            for r in reviews:
                self.note("new_review", "mysql", "order_reviews", {"review_id": r["review_id"]},
                          score=r["review_score"], order_id=r["order_id"])

    # ---- 3. address changes --------------------------------------------------
    def address_changes(self):
        cu = T["customers"]
        with self.my.begin() as c:
            for cid, _, _, old_city, old_state in self.rng.sample(self.customers, min(self.args.moves, len(self.customers))):
                _, _, zip_, city, state = self.rng.choice(self.customers)
                if (city, state) == (old_city, old_state):
                    continue
                c.execute(update(cu).where(cu.c.customer_id == cid).values(
                    customer_zip_code_prefix=zip_, customer_city=city, customer_state=state))
                self.note("address_change", "mysql", "customers", {"customer_id": cid},
                          city=city, state=state, old_city=old_city, old_state=old_state)

    # ---- 4b. dirt that touches existing rows ----------------------------------
    def inject_existing(self):
        k, rng, now = self.args.dirty, self.rng, self.now
        if not k:
            return
        r = T["order_reviews"]
        with self.my.begin() as c:
            pool = [x[0] for x in c.execute(select(r.c.review_pk))]
            for pk in rng.sample(pool, min(k, len(pool))):  # exact duplicate of an existing review
                row = c.execute(select(r).where(r.c.review_pk == pk)).mappings().one()
                values = {col: v for col, v in row.items() if col != "review_pk"}
                c.execute(insert(r).values(**values))
                self.note("duplicate_review", "mysql", "order_reviews", {"review_id": row["review_id"]})
            for oid in getattr(self, "new_order_ids", [])[:k]:  # scores outside 1..5
                rid = self.hexid()
                c.execute(insert(r).values(review_id=rid, order_id=oid, review_score=rng.choice([0, 6]),
                                           review_creation_date=now, review_answer_timestamp=now))
                self.note("bad_review_score", "mysql", "order_reviews", {"review_id": rid})
            old = [x[0] for x in c.execute(select(r.c.review_pk).where(r.c.review_creation_date >= SIM_EPOCH))]
            for pk in rng.sample(old, min(1, len(old))):  # a review disappears
                rid = c.execute(select(r.c.review_id).where(r.c.review_pk == pk)).scalar_one()
                c.execute(delete(r).where(r.c.review_pk == pk))
                self.note("deleted_review", "mysql", "order_reviews", {"review_pk": pk}, review_id=rid)
        o, i, p = T["orders"], T["order_items"], T["order_payments"]
        with self.ora.begin() as c:
            sim = [x[0] for x in c.execute(select(o.c.order_id).where(o.c.order_purchase_timestamp >= SIM_EPOCH))]
            for oid in rng.sample(sim, min(1, len(sim))):  # an order is hard-deleted
                for t in (p, i):
                    c.execute(delete(t).where(t.c.order_id == oid))
                c.execute(delete(o).where(o.c.order_id == oid))
                self.note("deleted_order", "oracle", "orders", {"order_id": oid})

    def write_log(self):
        path = Path(self.args.log)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for e in self.log:
                f.write(json.dumps(e) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--orders", type=int, default=50, help="new orders to create")
    ap.add_argument("--updates", type=int, default=30, help="open orders to move one step")
    ap.add_argument("--moves", type=int, default=5, help="customers who change address")
    ap.add_argument("--dirty", type=int, default=2, help="problems of each kind to inject (0 = none)")
    ap.add_argument("--now", type=datetime.fromisoformat, default=datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0),
                    help="pretend it is this UTC time (ISO format)")
    ap.add_argument("--seed", type=int, default=int(time.time()))
    ap.add_argument("--log", default=str(REPO / "logs" / "change_log.jsonl"))
    args = ap.parse_args(argv)

    sim = Sim(args)
    log_path = Path(args.log)
    if log_path.exists() and f'"run_id": "{sim.run_id}"' in log_path.read_text(encoding="utf-8"):
        print(f"ERROR: run {sim.run_id} is already in the change log. Use another --seed or --now.",
              file=sys.stderr)
        return 4
    sim.load_pools()
    sim.new_orders()
    sim.status_updates()
    sim.address_changes()
    sim.inject_existing()
    sim.write_log()
    counts = {}
    for e in sim.log:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    print(f"Run {sim.run_id}")
    for kind, n in sorted(counts.items()):
        print(f"  {kind:<22}{n}")
    print(f"Change log: {args.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
