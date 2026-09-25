Python timezone conversion reference

datetime.fromisoformat understands ISO datetime representations,
including UTC offsets. An aware datetime represents an instant.
astimezone(timezone.utc) converts that instant into UTC and may
change the calendar date. replace(tzinfo=timezone.utc) instead
changes the label without adjusting the wall-clock components.

The parser accepts some ISO forms that a narrower application
contract may disallow. Validate an explicitly required format
separately, and require an offset when naive local times would be
ambiguous. Fractional seconds are represented as microseconds.
