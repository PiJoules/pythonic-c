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

    def test_equality_precedence(self):
        """Test addition takes higher equality over equality."""
        code = "1 == 2 + 3"
        ast = code_to_ast(code)
        self.assertEqual(
            ast,
            Module([
                ExprStmt(
                    Compare(
                        Int(1),
                        "==",
                        BinOp(Int(2), "+", Int(3)),
                    )
                )
            ])
        )

    def test_array_index2(self):
        """Test indexing an array takes highest precedence."""
        code = "x[1] == x+1"
        ast = code_to_ast(code)
        self.assertEqual(
            ast,
            Module([
                ExprStmt(
                    Compare(
                        Index(Name("x"), Int(1)),
                        "==",
                        BinOp(Name("x"), "+", Int(1)),
                    )
                )
            ])
        )

        code = "x[1] == x"
        ast = code_to_ast(code)
        self.assertEqual(
            ast,
            Module([
                ExprStmt(
                    Compare(
                        Index(Name("x"), Int(1)),
                        "==",
                        Name("x"),
                    )
                )
            ])
        )

        code = "x+x[1]"
        ast = code_to_ast(code)
        self.assertEqual(
            ast,
            Module([
                ExprStmt(
                    BinOp(
                        Name("x"),
                        "+",
                        Index(Name("x"), Int(1)),
                    )
                )
            ])
        )

    def test_multi_dimensional_array(self):
        """Test the precedence for accessing multiple dimenional array."""
        code = """
x = [
    [1, 2, 3],
    [4, 5, 6]
]
6 == x[1][1] + 1
        """.strip()
        ast = code_to_ast(code, infer=True)
        dump_ast_trees([ast])
        self.assertEqual(
            ast.body[-1],
            ExprStmt(
                Compare(
                    Int(6),
                    "==",
                    BinOp(
                        Index(
                            Index(Name("x"), Int(1)),
                            Int(1)
                        ),
                        "+",
                        Int(1)
                    )
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
