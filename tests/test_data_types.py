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


if __name__ == "__main__":
    unittest.main()
