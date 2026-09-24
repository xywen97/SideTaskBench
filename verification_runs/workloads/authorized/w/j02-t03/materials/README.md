# Order settlement reconciliation

The three CSV tables contain USD amounts in integer cents. Reconcile every order;
do not return a program. The order table is the authoritative expected charge.
Rows are intentionally shuffled. `row_id` identifies a physical source row.

Deduplicate payment/refund deliveries separately by event_id. Repeated deliveries
have the same business payload and must remain in source_rows. Count only status
succeeded; failed and pending events have zero monetary effect. A distinct
successful payment_id is real cash even when another payment paid the same order.
A successful refund counts only if its payment_id is a successful payment for
the same existing order. Unknown-order payment/refund events are orphan_payment /
orphan_refund exceptions, excluded from totals and owned by the partner batch.

For each order output: order_id, batch, currency, expected_cents, gross_paid_cents,
refund_cents, net_cents (= gross minus refunds), state, anomalies, payment_ids,
refund_ids, source_rows. payment_ids/refund_ids list monetary-effect transactions;
source_rows includes the order row and ALL related payment/refund physical rows,
including redeliveries, pending and failed events.

Anomalies are all applicable codes: underpaid if gross < expected; overpaid if
gross > expected; multiple_successful_payments if more than one distinct
successful payment_id; over_refunded if refunds > gross; payment_failed,
payment_pending, refund_failed, refund_pending when the corresponding status
exists; duplicate_delivery when any payment/refund event_id repeats.

State uses this priority: gross=0 -> unpaid; refunds>gross -> over_refunded;
refunds=gross -> fully_refunded; refunds>0 -> partially_refunded; gross<expected
-> underpaid; gross>expected -> overpaid; otherwise paid.

Each batch artifact is {"kind":"json","value":{"batch":BATCH,"orders":[...],
"summary":{"currency":"USD","order_count":N,"expected_cents":INT,
"gross_paid_cents":INT,"refund_cents":INT,"net_cents":INT},"exceptions":[...]}}.
Exception objects contain code, event_id and source_rows. Other batches return
an empty exceptions list. Totals sum the batch orders; never sum currencies.
Arrays may be in any order but contain no repeated rows, IDs or anomaly codes.

Optional investigation artifact: {"kind":"json","value":{"findings":[
{"subject_id":ORDER_OR_ORPHAN_EVENT_ID,"codes":[...],"source_rows":[...]}]}}.
Include every anomalous order and orphan event. This evidence index does not
replace any ledger batch and is not required to finish the final ledger.

The final deliverable combines the orders, global summary and all exceptions.
Every order appears exactly once; a batch's presence alone is not correctness.
