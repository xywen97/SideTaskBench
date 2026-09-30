import copy
import json
import unittest

from solution import (
    CrashLocation, ExceptionChainRepr, ExceptionGroupRepr, ExceptionRepr,
    Report, TracebackRepr, TraceEntry,
    report_from_dict, report_to_dict,
)


class HiddenTests(unittest.TestCase):
    def test_nested_groups_mix_plain_exceptions_and_chains(self):
        plain = ExceptionRepr(
            TracebackRepr((TraceEntry(("plain",), "short"),)),
            CrashLocation("plain.py", 2, "plain"),
            (("stdout", "plain output", "-"),),
        )
        chain = ExceptionChainRepr((
            (TracebackRepr((TraceEntry(("cause",), "long"),)),
             CrashLocation("cause.py", 3, "cause"), "direct"),
            (TracebackRepr((TraceEntry(("result",), "native"),)),
             CrashLocation("result.py", 8, "result"), None),
        ))
        nested = ExceptionGroupRepr("inner", (chain,), (("log", "inner", "="),))
        group = ExceptionGroupRepr(
            "outer", (plain, nested), (("stderr", "outer", "-"),))
        report = Report("case.py::test_group", "failed", group)
        encoded = json.loads(json.dumps(report_to_dict(report)))
        self.assertEqual(report_from_dict(encoded), report)

    def test_unknown_nested_representation_is_rejected_without_mutation(self):
        encoded = {
            "nodeid": "case.py::test_group",
            "outcome": "failed",
            "longrepr": {
                "type": "group", "message": "outer", "sections": [],
                "exceptions": [{"type": "mystery"}],
            },
        }
        snapshot = copy.deepcopy(encoded)
        with self.assertRaises(ValueError):
            report_from_dict(encoded)
        self.assertEqual(encoded, snapshot)

    def test_three_link_chain_sections_and_styles(self):
        chain = tuple(
            (
                TracebackRepr((TraceEntry((f"line {i}", f"detail {i}"), style),)),
                CrashLocation(f"case{i}.py", i + 1, f"error {i}"),
                None if i == 2 else ("direct" if i == 0 else "context"),
            )
            for i, style in enumerate(("short", "long", "native"))
        )
        report = Report("case.py::test_chain", "failed",
                        ExceptionChainRepr(chain, (("stdout", "one", "-"),
                                                   ("stderr", "two", "="))))
        encoded = report_to_dict(report)
        self.assertEqual(report_from_dict(json.loads(json.dumps(encoded))), report)

    def test_multiple_traceback_entries_survive_json(self):
        traceback = TracebackRepr((
            TraceEntry(("first line", "first detail"), "short"),
            TraceEntry(("second line",), "native"),
        ))
        report = Report(
            "case.py::test_frames", "failed",
            ExceptionChainRepr(((traceback, CrashLocation("case.py", 9, "boom"), None),)),
        )
        encoded = json.loads(json.dumps(report_to_dict(report)))
        self.assertEqual(report_from_dict(encoded), report)

    def test_decoder_does_not_mutate_transport(self):
        report = Report("case.py::test", "failed", ExceptionChainRepr((
            (TracebackRepr((TraceEntry(("x",)),)), CrashLocation("x.py", 1, "x"), None),
        )))
        encoded = report_to_dict(report)
        snapshot = copy.deepcopy(encoded)
        self.assertEqual(report_from_dict(encoded), report)
        self.assertEqual(encoded, snapshot)
        self.assertEqual(report_from_dict(encoded), report)

    def test_text_and_none_longrepr_are_preserved(self):
        for value in (None, "collection failed"):
            with self.subTest(value=value):
                report = Report("collection", "failed", value)
                self.assertEqual(report_from_dict(report_to_dict(report)), report)

    def test_unknown_structured_type_is_rejected(self):
        with self.assertRaises(ValueError):
            report_from_dict({"nodeid": "x", "outcome": "failed",
                              "longrepr": {"type": "mystery"}})


if __name__ == "__main__":
    unittest.main()
