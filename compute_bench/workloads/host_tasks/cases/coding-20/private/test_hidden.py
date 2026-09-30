import copy
import unittest

from solution import read_rst_table, write_rst_table


class HiddenTests(unittest.TestCase):
    def test_empty_metadata_and_spaces_in_cells(self):
        columns = [
            {"name": "item", "unit": "", "dtype": "str", "values": ["red apple", "pear"]},
            {"name": "count", "unit": "items", "dtype": "int", "values": ["2", "10"]},
        ]
        headers = ("name", "unit", "dtype")
        text = write_rst_table(columns, header_rows=headers)
        self.assertEqual(read_rst_table(text, header_rows=headers), columns)

    def test_zero_data_rows(self):
        columns = [
            {"name": "a", "unit": "m", "values": []},
            {"name": "b", "unit": "s", "values": []},
        ]
        text = write_rst_table(columns, header_rows=("name", "unit"))
        self.assertEqual(read_rst_table(text, header_rows=("name", "unit")), columns)

    def test_writer_does_not_modify_input(self):
        columns = [{"name": "value", "dtype": "decimal", "values": ["-1.25", "0.00"]}]
        snapshot = copy.deepcopy(columns)
        write_rst_table(columns, header_rows=("name", "dtype"))
        self.assertEqual(columns, snapshot)

    def test_malformed_separators_and_boundaries_fail(self):
        malformed = (
            "=== ===\na   b\n=== ==\n1   2\n=== ===\n",
            "=== ===\na   b\n=== ===\n1234 2\n=== ===\n",
        )
        for text in malformed:
            with self.subTest(text=text), self.assertRaises(ValueError):
                read_rst_table(text)

    def test_trailing_content_outside_declared_width_fails(self):
        text = "=== ===\na   b\n=== ===\n1   2 trailing\n=== ===\n"
        with self.assertRaises(ValueError):
            read_rst_table(text)

    def test_duplicate_and_reserved_headers_fail(self):
        with self.assertRaises(ValueError):
            write_rst_table([{"name": "a", "values": []}],
                            header_rows=("name", "name"))
        with self.assertRaises(ValueError):
            write_rst_table([{"name": "a", "values": []}],
                            header_rows=("name", "values"))

    def test_multiline_headers_and_cells_fail(self):
        with self.assertRaises(ValueError):
            write_rst_table([{"name": "first\nsecond", "values": []}])
        with self.assertRaises(ValueError):
            write_rst_table([{"name": "a", "values": ["one\ntwo"]}])

    def test_unexpected_separator_inside_data_fails(self):
        text = "=== ===\na   b\n=== ===\n1   2\n=== ===\n3   4\n=== ===\n"
        with self.assertRaises(ValueError):
            read_rst_table(text)

    def test_unequal_columns_fail(self):
        columns = [
            {"name": "a", "values": ["1"]},
            {"name": "b", "values": ["2", "3"]},
        ]
        with self.assertRaises(ValueError):
            write_rst_table(columns)


if __name__ == "__main__":
    unittest.main()
