import unittest

from compiler import *


class TestFunctionDeclaration(unittest.TestCase):
    def test_default_return(self):
        """Test the default return type of a func decl with no specified
        return type is an int."""

        code = """
def func()
        """.strip()
        ast = code_to_ast(code, infer=True)
        self.assertEqual(ast.body[0].returns, "int")


if __name__ == "__main__":
    unittest.main()
