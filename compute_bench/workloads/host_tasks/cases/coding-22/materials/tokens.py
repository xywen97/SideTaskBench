"""Scan Python-style template text into literal and placeholder segments."""

_DOLLAR = "$"


def _is_name_start(char):
    return char == "_" or char.isalpha()


def _is_name_char(char):
    return char == "_" or char.isalnum()


def scan(text):
    """Split *text* into a list of ``(kind, value, raw)`` triples.

    ``kind`` is one of:

    * ``"text"`` - a literal run to emit verbatim; ``raw`` is the exact text.
    * ``"name"`` - a placeholder; ``value`` is the bare name and ``raw`` is the
      original ``$name`` or ``${name}`` spelling.
    * ``"invalid"`` - a ``$`` that begins no valid placeholder; ``value``
      equals ``raw``.
    """
    tokens = []
    literal = []
    index = 0
    length = len(text)

    def flush():
        if literal:
            run = "".join(literal)
            tokens.append(("text", run, run))
            literal.clear()

    while index < length:
        char = text[index]
        if char != _DOLLAR:
            literal.append(char)
            index += 1
            continue
        flush()
        if text.startswith("$$", index):
            tokens.append(("text", "$", "$"))
            index += 2
        elif index + 1 < length and _is_name_start(text[index + 1]):
            end = index + 1
            while end < length and _is_name_char(text[end]):
                end += 1
            tokens.append(("name", text[index + 1:end], text[index:end]))
            index = end
        elif index + 1 < length and text[index + 1] == "{":
            close = text.find("}", index + 2)
            inner = text[index + 2:close] if close >= 0 else ""
            if close >= 0 and inner and _is_name_start(inner[0]) and all(_is_name_char(c) for c in inner):
                tokens.append(("name", inner, text[index:close + 1]))
                index = close + 1
            else:
                end = close + 1 if close >= 0 else length
                tokens.append(("invalid", text[index:end], text[index:end]))
                index = end
        else:
            tokens.append(("invalid", char, char))
            index += 1
    flush()
    return tokens
