import unittest

from lang_utils import SlottedClass


class A(SlottedClass):
    __attrs__ = ("A", )


class Mixin:
    __attrs__ = ("B", )


class SlottedMixinWithAttrs(SlottedClass):
    __attrs__ = ("SB", )


class SlottedMixinNoAttrs(SlottedClass):
    __attrs__ = tuple()


class TestSlottedClass(unittest.TestCase):
    def test_must_inherit_slotted(self):
        """Test that all classes that one class inherits from must inherit from
        a SlottedClass."""
        with self.assertRaises(AssertionError):
            class B(A, Mixin):
                pass

    def test_inherit_with_multiple_attrs(self):
        """Test inheritting from multiple classes which both define attributes
        raises an error."""
        with self.assertRaises(RuntimeError):
            class B(A, SlottedMixinWithAttrs):
                pass

    def test_adding_new_attr(self):
        """Test that adding a new attribute that wasn't declared in __attrs__
        raises an error."""
        class B(A, SlottedMixinNoAttrs):
            __attrs__ = ("C", )

        x = B(A=1, C=3)

        with self.assertRaises(AttributeError):
            x.x = 4


if __name__ == "__main__":
    unittest.main()
