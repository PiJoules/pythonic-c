import unittest

from cparse import Parser
from lang_ast import *

p = Parser()


class TestExamples(unittest.TestCase):
    def setUp(self):
        self.__parser = p

    def __create_ast(self, code):
        return self.__parser.parse(code)

    def test_int_literal(self):
        """Test int literals."""
        ast = self.__create_ast("2")
        self.assertEqual(ast, Module([ExprStmt(Int(2))]))

    def test_float_literal(self):
        """Test float literals."""
        ast = self.__create_ast("2.0")
        self.assertEqual(ast, Module([ExprStmt(Float(2.0))]))

    def test_single_line_comment(self):
        """Test a single line comment."""
        code = """
# comment
        """
        ast = self.__create_ast(code)
        self.assertEqual(ast, Module(body=[]))

    def test_multiline_string_comment(self):
        """Test a multiline string comment."""
        code = '''
"""
multiline
    comment
"""
        '''
        ast = self.__create_ast(code)
        self.assertEqual(ast, Module([
            ExprStmt(Str("\nmultiline\n    comment\n"))
        ]))

    def test_define_stmt_no_value(self):
        """Test define statement with no dest value."""
        code = """
define CONSTANT
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            ast,
            Module([
                Define("CONSTANT", None)
            ])
        )

    def test_define_stmt(self):
        """Test define statement with a target value."""
        code = """
define DAYS_IN_A_YEAR 365
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            ast,
            Module([
                Define("DAYS_IN_A_YEAR", Int(365))
            ])
        )

    def test_enum_creation(self):
        """Test creating an enum type."""
        code = """

        """



if __name__ == "__main__":
    unittest.main()
