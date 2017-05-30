import unittest

from lang_ast import *
from compiler import *

"""
A lot of this will be testing based from:
http://en.cppreference.com/w/c/language/operator_precedence
"""


class TestPrecedence(unittest.TestCase):
    def test_comparison_chaining(self):
        """Test the order of chaining comparison operations."""
        code = "7 > 6 > 5"  # Should evaluate as (7 > 6) > 5
        ast = code_to_ast(code)
        self.assertEqual(
            ast,
            Module([
                ExprStmt(
                    Compare(
                        Compare(
                            Int(7),
                            ">",
                            Int(6)
                        ),
                        ">",
                        Int(5)
                    )
                )
            ])
        )

    def test_pre_post_inc_dec_precedence(self):
        """Test the precedence between post and pre increment and decrement."""
        code = "--j++"  # Not legal, but should evaluate as (--j)++
        ast = code_to_ast(code)
        self.assertEqual(
            ast,
            Module([
                ExprStmt(
                    PostInc(
                        PreDec(Name("j"))
                    )
                )
            ])
        )

    def test_arrow_post_inc_dec(self):
        """Test precedence between derefencing a struct pointer and
        incrementing the member"""
        code = "++x->a"  # Should evaluate as ++(x->a)
        ast = code_to_ast(code)
        dump_ast_trees([ast])
        self.assertEqual(
            ast,
            Module([
                ExprStmt(
                    PreInc(
                        StructPointerDeref(Name("x"), "a")
                    )
                )
            ])
        )


if __name__ == "__main__":
    unittest.main()
