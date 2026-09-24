# Add useful regression coverage for order payments

Deliver a unittest suite that protects the public Order state machine. The
provided order_service.py is correct. Do not edit it or existing public tests.
The evaluator runs submitted tests against the correct implementation and
independent private faulty variants. A useful contribution passes the correct
implementation and detects at least one fault. The final suite must detect all
declared-behavior faults in the private evaluation set; test/file counts are
not the objective. One sufficiently strong submitted suite can complete the job.

Order(total_cents): total is a positive integer; bool is not an integer amount.
capture(): only pending -> paid; a repeated capture raises ValueError.
cancel(): only pending -> cancelled; captured orders cannot be cancelled.
refund(amount): only paid/partially_refunded, positive integer cents (not bool),
at most the remaining balance. Accumulate refunds. A partial refund produces
partially_refunded; refunding the exact remainder produces refunded.
Invalid operations raise ValueError. summary() returns state, total_cents,
refunded_cents and remaining_cents (total minus refunded).

Submit discoverable unittest.TestCase classes. Allowed imports: unittest
(TestCase) and order_service (Order). Use public methods and unittest assertions.
No file/process access, reflection, global or object/module attribute mutation,
decorators, monkeypatches, skips, or replacements of unittest internals. Test
methods start test_; helper methods may start helper_. No unittest.main block.
Run public tests: python3 -m unittest discover -s tests -v

Optional evidence format: {scenarios:[{total_cents, actions, expected}]}.
Each action is {op: capture|cancel|refund, amount: integer when refunding}; at
most 12 actions. Expected is summary(), or {error: ValueError, at_step: index}
for the first rejected operation (zero-based). Such evidence is useful for
planning tests but cannot replace executable regression coverage.
