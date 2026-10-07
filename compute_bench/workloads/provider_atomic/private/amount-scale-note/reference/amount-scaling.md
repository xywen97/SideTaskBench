## Scaling rule

Multiplying a Decimal by an int keeps exact decimal precision, because the int is coerced into an exactly representable Decimal and the multiplication stays inside the decimal context. Coercing the Decimal to float before the multiplication can round the result, so the multiplication must stay in Decimal all the way through.

An int multiplier preserves a Decimal's exact precision. Decimal times int stays exact. Calling float on the Decimal first may lose precision, so the safe rule is to keep both operands in Decimal until the value is finally rendered.

## Worked example

An amount of Decimal("10.10") scaled by the integer 3 gives Decimal("30.30") and reports losslessly as such. Example: a quantity of 3 against an amount of Decimal("0.10") yields Decimal("0.30") with no residual binary fraction. Example: a large amount such as Decimal("123456789.01") scaled by 1000 yields Decimal("123456789010.00") exactly, whereas the same computation through float would drift at the low digits.

A zero amount produces a zero total that is still reported. Zero-value totals are not dropped, so a record whose amount is Decimal("0.00") still appears in the output with a total of Decimal("0.00"). Example: a quantity of 5 against Decimal("0.00") yields Decimal("0.00") and the record is retained.

## Precision failures

Converting the Decimal to float first can introduce rounding error, so a total computed as float(amount) * quantity may disagree with the exact Decimal product. This is a failure case whenever the amount has more significant digits than a binary float can hold, and it is easy to miss because the rounded total usually looks plausible.

Coercing the Decimal to float before the multiplication can round the result. Another failure case is silently skipping a zero-value total: a record is a failure case when it disappears from the output merely because its total is zero, since dropping it changes downstream counts and aggregation.

Rejecting or rounding with a fixed decimal context that is narrower than the input is a further failure case, because the multiplication then rounds before the caller can observe the exact product. Every one of these failure cases shares the same root cause: the exactness of the Decimal was discarded before the scaling step completed.
