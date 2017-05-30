import unittest

from compiler import *


class TestDataTypes(unittest.TestCase):
    def test_long(self):
        """Test that a long in language space gets converted to a long long in
        C space."""
        code = """
x: long
        """.strip()
        ast = code_to_ast(code, infer=True)
        self.assertEqual(ast.c_code(), """
long long x;
                         """.strip())

    def test_str_init(self):
        """Test the first assignment of a variable to a string makes it a
        char array."""
        code = "x = \"somestring\""
        ast = code_to_ast(code, infer=True)
        dump_ast_trees([ast])
        self.assertEqual(
            ast,
            Module([
                CInclude("stdlib.h"),
                VarDeclStmt(
                    VarDecl(
                        "x",
                        Array(NameType("char"), Int(11)),
                        Str("somestring")
                    )
                )
            ])
        )


if __name__ == "__main__":
    unittest.main()
