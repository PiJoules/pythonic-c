import unittest

from compiler import *


class TestClass(unittest.TestCase):
    def test_empty_class_syntax(self):
        """Test creating an empty class."""
        code = """
class A:
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(
                name="A",
                body=[Pass()]
            )
        )

    def test_generic_class_syntax(self):
        """Test creating a class with generic types."""
        code = """
class A[]:
    pass
        """.strip()
        with self.assertRaises(SyntaxError):
            code_to_ast(code)

        code = """
class A[T]:
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(name="A", generics=["T"], body=[Pass()])
        )

        code = """
class A[T, ]:
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(name="A", generics=["T"], body=[Pass()])
        )

        code = """
class A[T, U, V]:
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(name="A", generics=["T", "U", "V"], body=[Pass()])
        )

        code = """
class A[T, U, V,]:
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(name="A", generics=["T", "U", "V"], body=[Pass()])
        )


if __name__ == "__main__":
    unittest.main()
