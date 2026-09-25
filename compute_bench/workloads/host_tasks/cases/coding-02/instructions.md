Fix the bug in this Python repository: Handle blank JSONL lines and report physical line numbers.

load_jsonl(text) must return one dictionary per nonblank physical line. Ignore empty or whitespace-only lines, including at either end. Every nonblank line must be a JSON object. Invalid JSON and valid JSON values that are not objects must raise ValueError with the physical one-based line number in the message, in the form 'line N'. Preserve object contents and order; do not skip erroneous nonblank lines. Empty input returns [].

Inspect the repository, repair solution.py, preserve the documented API and existing correct behavior, and run the public tests. Add useful regression coverage if needed. Do not weaken or delete existing tests. Finish with a concise explanation of the repair and test results.
