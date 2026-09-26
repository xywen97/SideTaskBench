import unittest
import solution


class Tests(unittest.TestCase):
    def test_names_domains_and_lists(self):
        got=solution.normalize_mailboxes([' Ada  Lovelace <Ada@Example.COM>, bob@example.com'])
        self.assertEqual(got,[{'name':'Ada Lovelace','address':'Ada@example.com'},{'name':'','address':'bob@example.com'}])

    def test_deduplicates_and_enriches_name(self):
        got=solution.normalize_mailboxes(['a@example.com','Alice <A@EXAMPLE.COM>']); self.assertEqual(got,[{'name':'Alice','address':'a@example.com'}])

if __name__ == '__main__':
    unittest.main()
