Cursor pagination reference

A cursor is an opaque continuation token. Termination is represented
by a null next cursor, not by the number of items on a page. Therefore
an empty page may still lead to later results. Clients should retain a
set of cursors already fetched: seeing a token twice proves that the
reachable chain contains a cycle and prevents an unbounded loop.

The initial cursor may itself be null. Item order is page order followed
by order within each page. Cursor values should not be interpreted or
rewritten by the client.
