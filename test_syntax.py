import unittest

from cparse import Parser
from lang_ast import *

PARSER = Parser()


class TestSyntax(unittest.TestCase):
    def __create_ast(self, code):
        return PARSER.parse(code)

    ###### Types ######

    def test_int_literal(self):
        """Test int literals."""
        ast = self.__create_ast("2")
        self.assertEqual(ast, Module([ExprStmt(Int(2))]))

    def test_float_literal(self):
        """Test float literals."""
        ast = self.__create_ast("2.0")
        self.assertEqual(ast, Module([ExprStmt(Float(2.0))]))

    ###### Comments ########

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

    ####### Statements #############

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
enum days {MON, TUE, WED, THU, FRI, SAT, SUN}
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            ast,
            Module([
                Enum("days", [
                    "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"
                ])
            ])
        )

    def test_include_standard(self):
        """Test standard systen include."""
        code = """
include "stdio.h"
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            ast,
            Module([
                Include(Str("stdio.h"))
            ])
        )

    def test_include_local(self):
        """Test local header include."""
        code = """
includel "myheader.h"
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            ast,
            Module([
                IncludeLocal(Str("myheader.h"))
            ])
        )

    ########### Control flow ######

    def test_if(self):
        """Test regular if."""
        code = """
if x:
    pass
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            ast,
            Module([
                If(
                    Name("x", None),
                    [Pass()],
                    []
                )
            ])
        )
        self.assertEqual(
            str(ast),
            code.strip()
        )
        self.assertEqual(
            ast.c_code(),
            """
if (x) {
}
            """.strip()
        )

    def test_elif(self):
        """Test single elif."""
        code = """
if x:
    pass
    pass
elif y:
    pass
    pass
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            str(ast),
            code.strip()
        )
        self.assertEqual(
            ast.c_code(),
            """
if (x) {
}
else if (y) {
}
            """.strip()
        )

    def test_elif_multiple(self):
        """Test multiple elif blocks."""
        code = """
if x:
    pass
elif y:
    pass
elif z:
    pass
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            str(ast),
            code.strip()
        )
        self.assertEqual(
            ast.c_code(),
            """
if (x) {
}
else if (y) {
}
else if (z) {
}
            """.strip()
        )

    def test_else_block(self):
        """Test just an else block."""
        code = """
if x:
    pass
else:
    pass
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            str(ast),
            code.strip()
        )
        self.assertEqual(
            ast.c_code(),
            """
if (x) {
}
else {
}
            """.strip()
        )

    def test_full_if_ladder(self):
        """Test an if, elif, and else together"""
        code = """
if x:
    pass
elif y:
    pass
else:
    pass
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            str(ast),
            code.strip()
        )
        self.assertEqual(
            ast.c_code(),
            """
if (x) {
}
else if (y) {
}
else {
}
            """.strip()
        )

    def test_nested_if_in_else(self):
        """
        Test that a single nested if in an else block gets expanded to an
        elif block while an else containing other statements stays the same.
        """
        code = """
if x:
    pass
else:
    if y:
        pass
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            str(ast),
            """
if x:
    pass
elif y:
    pass
            """.strip()
        )
        self.assertEqual(
            ast.c_code(),
            """
if (x) {
}
else if (y) {
}
            """.strip()
        )

        # Else contains something else
        code = """
if x:
    pass
else:
    if y:
        pass
    func()
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            str(ast),
            code.strip()
        )
        self.assertEqual(
            ast.c_code(),
            """
if (x) {
}
else {
    if (y) {
    }
    func();
}
            """.strip()
        )

    def test_while(self):
        """Test while loop."""
        code = """
while x:
    func()
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            ast,
            Module([
                While(Name("x"), [
                    ExprStmt(Call(Name("func")))
                ])
            ])
        )
        self.assertEqual(
            str(ast),
            code.strip()
        )
        self.assertEqual(
            ast.c_code(),
            """
while (x) {
    func();
}
            """.strip()
        )

    def test_while_with_orelse(self):
        """Test a while loop with an orelse block."""
        code = """
while x:
    func()
else:
    func2()
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            ast,
            Module([
                While(Name("x"), [
                    ExprStmt(Call(Name("func")))
                ], [
                    ExprStmt(Call(Name("func2")))
                ])
            ])
        )
        self.assertEqual(
            str(ast),
            code.strip()
        )
        self.assertEqual(
            ast.c_code(),
            """
while (1) {
    if (x) {
        func();
    }
    else {
        func2();
        break;
    }
}
            """.strip()
        )

    def test_do_while(self):
        """Test a do whike statement."""
        code = """
do:
    func()
while x
        """
        ast = self.__create_ast(code)
        self.assertEqual(
            ast,
            Module([
                DoWhile(Name("x"), [
                    ExprStmt(Call(Name("func")))
                ])
            ])
        )
        self.assertEqual(
            str(ast),
            code.strip()
        )
        self.assertEqual(
            ast.c_code(),
            """
do {
    func();
} while (x);
            """.strip()
        )


if __name__ == "__main__":
    unittest.main()
