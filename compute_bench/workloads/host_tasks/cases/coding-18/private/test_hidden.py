import unittest

from solution import Mark, get_unpacked_marks, store_mark


class HiddenTests(unittest.TestCase):
    def test_diamond_follows_python_mro_once(self):
        class Root:
            pytestmark = Mark("root")

        class Left(Root):
            pytestmark = [Mark("left")]

        class Right(Root):
            pytestmark = [Mark("right")]

        class Leaf(Left, Right):
            pytestmark = Mark("leaf")

        self.assertEqual(
            get_unpacked_marks(Leaf),
            [Mark("leaf"), Mark("left"), Mark("right"), Mark("root")],
        )
        self.assertEqual(get_unpacked_marks(Leaf, consider_mro=False), [Mark("leaf")])

    def test_repeated_names_are_not_deduplicated(self):
        class A:
            pytestmark = [Mark("tag", (1,))]

        class B:
            pytestmark = [Mark("tag", (2,))]

        class C(A, B):
            pass

        self.assertEqual(get_unpacked_marks(C), [Mark("tag", (1,)), Mark("tag", (2,))])

    def test_repeated_store_preserves_direct_order(self):
        class Base:
            pytestmark = [Mark("base")]

        class Child(Base):
            pass

        store_mark(Child, Mark("one"))
        store_mark(Child, Mark("two"))
        self.assertEqual(get_unpacked_marks(Child),
                         [Mark("one"), Mark("two"), Mark("base")])
        self.assertEqual(Base.pytestmark, [Mark("base")])

    def test_returned_collection_does_not_alias_direct_storage(self):
        stored = [Mark("kept")]

        class Item:
            pytestmark = stored

        returned = get_unpacked_marks(Item, consider_mro=False)
        returned.append(Mark("temporary"))
        self.assertEqual(Item.pytestmark, [Mark("kept")])

    def test_non_class_object_uses_normal_attribute(self):
        class Holder:
            pass

        value = Holder()
        value.pytestmark = Mark("instance")
        self.assertEqual(get_unpacked_marks(value), [Mark("instance")])
        store_mark(value, Mark("later"))
        self.assertEqual(get_unpacked_marks(value), [Mark("instance"), Mark("later")])


if __name__ == "__main__":
    unittest.main()
