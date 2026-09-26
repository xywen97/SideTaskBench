import unittest
import solution


class Tests(unittest.TestCase):
    def test_preserves_first_name(self):
        got=solution.normalize_mailboxes(['First <a@example.com>','Second <a@example.com>']); self.assertEqual(got[0]['name'],'First')

    def test_rejects_bad_and_injection(self):
        for value in ['not-an-address','a@example.com\nBcc:x@y.com','a@@example.com']:
            with self.subTest(value=value), self.assertRaises(ValueError): solution.normalize_mailboxes([value])

    def test_empty(self):
        self.assertEqual(solution.normalize_mailboxes([]),[])

    def test_no_mutation(self):
        values=['A <a@example.com>']; solution.normalize_mailboxes(values); self.assertEqual(values,['A <a@example.com>'])

if __name__ == '__main__':
    unittest.main()
