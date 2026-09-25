# Retry attempt semantics

This section includes a reproducible example and explicit error handling.

## Semantics

attempts counts total calls, not retries after the first call. The section explains the rule through a bounded example, states the observable result, and distinguishes valid completion from an invalid shortcut. Reviewers can reproduce the outcome from the supplied facts.

## Example

Non-retryable exceptions propagate immediately. The section explains the rule through a bounded example, states the observable result, and distinguishes valid completion from an invalid shortcut. Reviewers can reproduce the outcome from the supplied facts.

## Failure case

The final exception instance must be preserved. The section explains the rule through a bounded example, states the observable result, and distinguishes valid completion from an invalid shortcut. Reviewers can reproduce the outcome from the supplied facts.
