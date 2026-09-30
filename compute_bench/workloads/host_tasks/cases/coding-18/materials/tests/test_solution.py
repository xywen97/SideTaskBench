import unittest

from solution import Mark, get_unpacked_marks, store_mark


class PublicTests(unittest.TestCase):
    def test_direct_marks_are_returned(self):
        class Item:
            pytestmark = Mark("direct")

        self.assertEqual(get_unpacked_marks(Item), [Mark("direct")])

    def test_store_appends_to_an_object(self):
        class Holder:
            pass

        value = Holder()
        store_mark(value, Mark("first"))
        store_mark(value, Mark("second"))
        self.assertEqual(get_unpacked_marks(value), [Mark("first"), Mark("second")])

    def test_subclass_update_leaves_base_unchanged(self):
        class Base:
            pytestmark = [Mark("base")]

        class Child(Base):
            pass

        store_mark(Child, Mark("child"))
        self.assertEqual(Base.pytestmark, [Mark("base")])
        self.assertEqual(Child.__dict__["pytestmark"], [Mark("child")])


if __name__ == "__main__":
    unittest.main()
