import unittest

from compiler import *
from lang_ast import *


class TestIndexing(unittest.TestCase):
    def test_long(self):
        """Test indexing an array goes inside to outside."""
        code = """
arr[1][2][3]
        """.strip()
        ast = code_to_ast(code)
        self.assertEqual(
            ast,
            Module([
                ExprStmt(
                    Index(
                        Index(
                            Index(
                                Name("arr"),
                                Int(1)
                            ),
                            Int(2)
                        ),
                        Int(3)
                    )
                )
            ])
        )


if __name__ == "__main__":
    unittest.main()
