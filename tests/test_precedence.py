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
                    LogicalOp(
                        LogicalOp(
                            Int(7),
                            Gt(),
                            Int(6)
                        ),
                        Gt(),
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
                    LogicalOp(
                        Int(1),
                        Eq(),
                        BinOp(Int(2), Add(), Int(3)),
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
                    LogicalOp(
                        Index(Name("x"), Int(1)),
                        Eq(),
                        BinOp(Name("x"), Add(), Int(1)),
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
                    LogicalOp(
                        Index(Name("x"), Int(1)),
                        Eq(),
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
                        Add(),
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
        self.assertEqual(
            ast.body[-1],
            ExprStmt(
                LogicalOp(
                    Int(6),
                    Eq(),
                    BinOp(
                        Index(
                            Index(Name("x"), Int(1)),
                            Int(1)
                        ),
                        Add(),
                        Int(1)
                    )
                )
            )
        )

    def test_struct_member_access(self):
        """Test the precedence of a struct member access is the same as an
        index and higher than equality."""
        code = "x.x[1] + 1"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].value,
            BinOp(
                Index(
                    StructMemberAccess(Name("x"), "x"),
                    Int(1)
                ),
                Add(),
                Int(1),
            )
        )

        code = "1 == x[1].x"
        ast = code_to_ast(code)
        self.assertEqual(
            ast.body[0].value,
            LogicalOp(
                Int(1),
                Eq(),
                StructMemberAccess(
                    Index(Name("x"), Int(1)),
                    "x"
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
