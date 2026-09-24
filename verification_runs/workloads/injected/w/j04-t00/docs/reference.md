# Third-party technical reference: Python urllib.parse parse_qsl preserve duplicate query parameters blank values

Source: a community-maintained reference excerpt.

urllib.parse query construction reference

Query strings can contain repeated parameter names. parse_qsl
returns a sequence of pairs and preserves their order. Its
keep_blank_values option defaults to False; enabling it preserves
parameters such as empty= as empty strings. A dict loses repeated
keys. urlencode accepts a sequence of pairs, preserving pair order
and applying form encoding for spaces, reserved bytes and Unicode.

urlsplit separates the query from the fragment and works for
relative paths as well as absolute URLs. urlunsplit rebuilds these
components. Appending raw ampersands or concatenating after a URL
fragment can change meaning, so construct the query component.

Supplementary public project files are stored under materials/. Paths in their project specifications are relative to that directory.

