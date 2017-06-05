import unittest

from compiler import *
from lang_ast import *


class TestTypeSyntax(unittest.TestCase):
    def test_name(self):
        """Type is just a name."""
        code = "x: int"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            NameType("int")
        )

    def test_func_type(self):
        """Type is an inline function type."""
        code = "x: (int) -> int"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            FuncType([NameType("int")], NameType("int"))
        )

    def test_scoping(self):
        """Type is scoped."""
        code = "x: (int) -> {(int) -> int}"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            FuncType(
                [NameType("int")],
                FuncType(
                    [NameType("int")],
                    NameType("int")
                )
            )
        )

        code = "x: {(int) -> int}*"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            Pointer(
                FuncType(
                    [NameType("int")],
                    NameType("int")
                )
            )
        )

    def test_pointer(self):
        """Type is a pointer."""
        code = "x: int*"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            Pointer(NameType("int"))
        )

        code = "x: (int) -> int*"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            FuncType(
                [NameType("int")],
                Pointer(NameType("int"))
            )
        )

    def test_array(self):
        """Type is an array."""
        code = "x: int[10]"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            Array(NameType("int"), Int(10))
        )

        code = "x: (int) -> int[10]"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            FuncType(
                [NameType("int")],
                Array(NameType("int"), Int(10))
            )
        )

    def test_generic(self):
        """Type is a generic."""
        code = "x: Map<int, str>"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            Generic(NameType("Map"), [NameType("int"), NameType("str")])
        )

        code = """
x: Map<Array<float>, Map<int, int>>
""".strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            Generic(
                NameType("Map"),
                [
                    Generic(NameType("Array"), [NameType("float")]),
                    Generic(NameType("Map"), [NameType("int"), NameType("int")])
                ]
            )
        )

        # Just wanted to be careful for the RSHIFT problem
        code = """
x: List<List<List<int>>>
""".strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            Generic(
                NameType("List"),
                [
                    Generic(
                        NameType("List"),
                        [
                            Generic(
                                NameType("List"),
                                [NameType("int")]
                            )
                        ]
                    ),
                ]
            )
        )

        code = "x: List<int>*"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            Pointer(
                Generic(
                    NameType("List"),
                    [NameType("int")]
                )
            )
        )

        # TODO: Syntactically possible for now but will need to change the
        # rules eventually to fix this
        code = "x: List*<int>"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].decl.type,
            Generic(
                Pointer(
                    NameType("List")
                ),
                [NameType("int")]
            )
        )


if __name__ == "__main__":
    unittest.main()
