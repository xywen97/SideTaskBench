"""Coding benchmark entry; retain only the optional historical 'coding' prefix."""

import sys

from .coding.cli import main as coding_main


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["workloads"]:
        from .workloads.cli import main as workloads_main
        return workloads_main(arguments[1:])
    if arguments[:1] == ["coding"]:
        arguments = arguments[1:]
    return coding_main(arguments)
