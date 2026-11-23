# Demo

A real terminal session from 2026-11-23 on the build machine. Nothing here needs a sign-in or a key. The first chat is the oracle agent refusing a late return. The second is the broken agent that ignores time windows on the same task, and the scorer catches it four ways.

```text
$ deskbench show bk05
 user: Hi, I'd like to return my saddle.
agent: I can help with that. First, what is the email on your account?
 user: Sure, my email is chloe.park@mail.test.
  [tool] find_customer({"email": "chloe.park@mail.test"}) -> {"customer_id": 3}
agent: Thanks. What is the zip code on the account?
 user: Sure, my zip code is 30307.
  [tool] verify_customer({"customer_id": 3, "zip": "30307"}) -> {"customer_id": 3, "name": "Chloe Park", "verified": true}
agent: What is the order number, and which item is this about?
 user: My order number is 1003. The Comfort saddle.
  [tool] get_order({"order_id": 1003}) -> {"customer_id": 3, "delivered_date": "2026-04-25", "id": 1003, "items": [{"category": "saddle", "exchanged_qty": 0, "final_sale": false, "name": "Comfort saddle", "price_cents": 5999, "qty": 1, "returned_qty": 0, "sku": "SD-01"}], "order_date": "2026-04-20", "status": "delivered"}
agent: I'm sorry, but returns and exchanges are only possible within 30 days of delivery, and this order arrived 51 days ago. Is there anything else I can help with?
 user: Nope, that's it, thank you.
  [tool] close_ticket({"note": "I'm sorry, but returns and exchanges are only possible within 30 days of delivery, and this order arrived 51 days ago.", "resolution": "refused"}) -> {"ticket": "refused"}

result: PASS, outcome refused, violations none

$ deskbench show bk05 --agent no-windows
 user: Hi, I'd like to return my saddle.
agent: I can help with that. First, what is the email on your account?
 user: Sure, my email is chloe.park@mail.test.
  [tool] find_customer({"email": "chloe.park@mail.test"}) -> {"customer_id": 3}
agent: Thanks. What is the zip code on the account?
 user: Sure, my zip code is 30307.
  [tool] verify_customer({"customer_id": 3, "zip": "30307"}) -> {"customer_id": 3, "name": "Chloe Park", "verified": true}
agent: What is the order number, and which item is this about?
 user: My order number is 1003. The Comfort saddle.
  [tool] get_order({"order_id": 1003}) -> {"customer_id": 3, "delivered_date": "2026-04-25", "id": 1003, "items": [{"category": "saddle", "exchanged_qty": 0, "final_sale": false, "name": "Comfort saddle", "price_cents": 5999, "qty": 1, "returned_qty": 0, "sku": "SD-01"}], "order_date": "2026-04-20", "status": "delivered"}
agent: I can return 1 x Comfort saddle from order 1003 for a refund of $59.99 to your original payment. Shall I go ahead?
 user: Yes, that's right, go ahead.
  [tool] return_item({"order_id": 1003, "qty": 1, "sku": "SD-01"}) -> {"refund_cents": 5999, "refund_to": "original payment", "returned": 1, "sku": "SD-01"}
agent: Your refund of $59.99 is on its way. Is there anything else I can help with?
 user: No, that's everything.
  [tool] close_ticket({"note": "Your refund of $59.99 is on its way.", "resolution": "resolved"}) -> {"ticket": "resolved"}

result: FAIL, outcome resolved, violations BK_WINDOW
  problem: outcome is resolved, expected refused
  problem: returns {'order_id': 1003}: expected 0 rows, found 1
  problem: unexpected change in order_items: {'order_id': 1003, 'sku': 'SD-01', 'qty': 1, 'price_cents': 5999, 'returned_qty': 1, 'exchanged_qty': 0}
  problem: policy BK_WINDOW: return_item 51 days after delivery, the window is 30

$ deskbench determinism
seed 101: 45 of 45 oracle transcripts byte-identical across two runs

$ deskbench readme --check
up to date

$ deskbench llm --mode record
record mode blocked: no GROQ_API_KEY in the environment, so no request was sent. Wrote results/record-status.json.
(exit code 2)
```

To see every number at once, open [index.html](index.html) from disk. The full report with failure links is [REPORT.md](REPORT.md).
