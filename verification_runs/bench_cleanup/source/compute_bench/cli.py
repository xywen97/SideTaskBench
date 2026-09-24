"""Coding benchmark entry; retain only the optional historical 'coding' prefix."""

import sys

from .coding.cli import main as coding_main


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["coding"]:
        arguments = arguments[1:]
    return coding_main(arguments)
