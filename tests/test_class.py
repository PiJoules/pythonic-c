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
class A<>:
    pass
        """.strip()
        with self.assertRaises(SyntaxError):
            code_to_ast(code)

        code = """
class A<T>:
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(name="A", generics=["T"], body=[Pass()])
        )

        code = """
class A<T, >:
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(name="A", generics=["T"], body=[Pass()])
        )

        code = """
class A<T, U, V>:
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(name="A", generics=["T", "U", "V"], body=[Pass()])
        )

        code = """
class A<T, U, V,>:
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(name="A", generics=["T", "U", "V"], body=[Pass()])
        )

    def test_parents_syntax(self):
        """Test creating a class with parents."""
        code = """
class A():
    pass
        """.strip()
        with self.assertRaises(SyntaxError):
            code_to_ast(code)

        code = """
class A(B):
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(name="A", parents=[NameType("B")], body=[Pass()])
        )

        code = """
class A(B, ):
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(name="A", parents=[NameType("B")], body=[Pass()])
        )

        code = """
class A(B, List<B>):
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(
                name="A",
                parents=[
                    NameType("B"),
                    Generic(NameType("List"), [NameType("B")])
                ],
                body=[Pass()]
            )
        )

    def test_generics_and_parents(self):
        """Class has generics and parents."""
        code = """
class A<T, U>(B, List<B>):
    pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(
                name="A",
                generics=["T", "U"],
                parents=[
                    NameType("B"),
                    Generic(NameType("List"), [NameType("B")])
                ],
                body=[Pass()]
            )
        )

    def test_class_with_body(self):
        """The class has a body now."""
        code = """
class A:
    x: int = 0

    def func(self, x):
        pass
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0],
            ClassDef(
                name="A",
                body=[
                    VarDeclStmt(
                        VarDecl("x", NameType("int"), Int(0))
                    ),
                    FuncDef(
                        "func",
                        ["self", "x"],
                        [Pass()]
                    )
                ]
            )
        )


if __name__ == "__main__":
    unittest.main()
