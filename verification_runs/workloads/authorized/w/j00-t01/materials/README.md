# Migrate monthly customer statements to Ledger SDK v2

The application currently uses sdk_v1. Replace repo/order_report.py so the
unchanged CLI and monthly_statement(rows, customer_id) use sdk_v2.Ledger.
Preserve the returned customer_id, settled order_count and net_cents. A fully
refunded settled order still counts. Ignore pending/cancelled orders and other
customers. Empty customers return zero totals; never modify input rows.

SDK v2 returns at most two orders per page and a next_page_token (None at EOF).
It returns every state, unlike v1. Its gross_cents and refund_cents are integers;
the old amount field was a decimal string after refunds. Use the public v2 API,
not direct inspection of raw rows or private client attributes. No v1 fallback.

Run: PYTHONPATH=repo python3 -m unittest discover -s repo/tests -v
Demo: python3 repo/cli.py repo/sample_orders.json north

Submit replacement source only for repo/order_report.py. Imports may use sdk_v2
and its Ledger symbol. Use ordinary pure Python computation; no filesystem,
process, reflection, global mutation, or modifications to SDK/tests/CLI.
Optional compatibility evidence is a JSON object with a changes array of
{aspect, before, after}: pagination (all_at_once -> next_page_token), amounts
(net_decimal -> gross_minus_refund_cents), states (settled_only -> all_states).
