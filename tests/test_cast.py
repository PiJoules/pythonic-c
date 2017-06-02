import unittest

from compiler import *


class TestCast(unittest.TestCase):
    def test_cast_precedence(self):
        """Test that a cast has right associativity and comes before mult and
        div."""
        code = """
<float> 2 / 4
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast,
            Module([
                ExprStmt(
                    BinOp(
                        Cast(
                            NameType("float"),
                            Int(2),
                        ),
                        Div(),
                        Int(4)
                    )
                )
            ])
        )


if __name__ == "__main__":
    unittest.main()
