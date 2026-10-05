"""Render template strings using a value mapping."""

from tokens import scan


class MissingPlaceholder(KeyError):
    """Raised when a placeholder has no value and safe mode is off."""


def substitute(text, mapping, safe=False):
    """Return *text* with every placeholder replaced from *mapping*.

    ``$$`` produces a single dollar sign.  ``$name`` and ``${name}`` produce
    ``str(mapping["name"])``.  An unresolved placeholder raises
    ``MissingPlaceholder`` unless *safe* is true, in which case the original
    placeholder spelling is kept.  Any other dollar sequence raises
    ``ValueError``.  *mapping* is never mutated.
    """
    pieces = []
    for kind, value, raw in scan(text):
        if kind == "text":
            pieces.append(raw)
        elif kind == "name":
            if value in mapping:
                pieces.append(str(mapping[value]))
            elif safe:
                pieces.append(raw)
            else:
                raise MissingPlaceholder(value)
        else:
            raise ValueError("invalid placeholder: " + raw)
    return "".join(pieces)
