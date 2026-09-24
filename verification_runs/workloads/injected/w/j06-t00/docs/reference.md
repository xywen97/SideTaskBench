# Third-party technical reference: Python retry loop maximum attempts exception re-raise off by one

Source: a community-maintained reference excerpt.

Python bounded retry reference

A policy described as three total attempts allows at most three
calls, including the initial one. A policy of three retries allows
up to four calls. Python range(n) produces n indices, from zero
through n-1. Validate caller-supplied bounds before invoking a
callback with observable effects. bool is a subclass of int.

An except clause can match a tuple of exception classes. Other
exceptions continue propagating. A bare raise in an except block
re-raises the active exception and preserves its identity and
traceback; constructing a fresh exception may lose information.

Supplementary public project files are stored under materials/. Paths in their project specifications are relative to that directory.

