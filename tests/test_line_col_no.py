import unittest
import ply.lex as lex

from clex import Lexer, find_column


class TokenWrap:
    def __init__(self, t, value, lineno, colno):
        self.type = t
        self.value = value
        self.lineno = lineno
        self.colno = colno

    def __eq__(self, other):
        if isinstance(other, NewlineWrap):
            return other == self

        return (
            self.type == other.type and
            self.value == other.value and
            self.lineno == other.lineno and
            self.colno == other.colno
        )

    @classmethod
    def from_lex_token(cls, tok):
        return cls(
            tok.type,
            tok.value,
            tok.lineno,
            find_column(tok)
        )

    def __str__(self):
        return "TokenWrap({},'{}',{},{})".format(
            self.type,
            self.value.replace("\n", "\\n"),
            self.lineno,
            self.colno
        )


class NewlineWrap(TokenWrap):
    def __init__(self, lineno):
        super().__init__("NEWLINE", "\n", lineno, -1)

    def __eq__(self, other):
        return (
            other.type == "NEWLINE" and
            self.lineno == other.lineno
        )


class TestLineColNo(unittest.TestCase):
    def skip(self, n=1):
        """Skip first n tokens"""
        for i in range(n):
            self.lexer.token()

    def skip_line(self, n=1):
        """Skip n whole lines."""
        for i in range(n):
            while self.lexer.token().type != "NEWLINE":
                pass

    def assert_tokens_equal(self, lex_token, token_wrap):
        """Compare a LexToken to a TokenWrap"""
        assert isinstance(lex_token, lex.LexToken)
        assert isinstance(token_wrap, TokenWrap)

        found = TokenWrap.from_lex_token(lex_token)

        assert found == token_wrap, "Found {}. Expected {}.".format(found, token_wrap)

    def assert_token_line(self, *token_wraps):
        """Compare a line of tokens excluding the newline"""
        lexer = self.lexer
        last = None
        for token_wrap in token_wraps:
            last = token_wrap
            self.assert_tokens_equal(lexer.token(), token_wrap)
        self.assert_tokens_equal(lexer.token(), NewlineWrap(last.lineno))

    def assert_newline(self, lineno):
        self.assert_tokens_equal(self.lexer.token(), NewlineWrap(lineno))

    def test_alignment_example(self):
        with open("examples/alignment_test.cu", "r") as f:
            code = f.read()

        self.lexer = lexer = Lexer()
        lexer.input(code)

        # First quote
        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("STRING", "double quote comment", 3, 1)
        )

        self.assert_tokens_equal(
            lexer.token(),
            NewlineWrap(3)
        )

        # Multiline string
        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("STRING", "\nmultiline\ndouble\nquotes\n", 5, 1)
        )

        self.assert_tokens_equal(
            lexer.token(),
            NewlineWrap(9)
        )

        # define 1
        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("DEFINE", "define", 12, 1)
        )

        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("NAME", "CONSTANT", 12, 8)
        )

        self.assert_tokens_equal(
            lexer.token(),
            NewlineWrap(12)
        )

        # define 2
        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("DEFINE", "define", 13, 1)
        )

        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("NAME", "DAYS_IN_A_YEAR", 13, 8)
        )

        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("INT", 365, 13, 23)
        )

        self.assert_tokens_equal(
            lexer.token(),
            NewlineWrap(13)
        )

        # Include
        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("INCLUDE", "include", 15, 1)
        )

        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("STRING", "stdio.h", 15, 9)
        )

        self.assert_tokens_equal(
            lexer.token(),
            NewlineWrap(15)
        )

        # Include local
        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("INCLUDE_LOCAL", "includel", 16, 1)
        )

        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("STRING", "myheader.h", 16, 10)
        )

        self.assert_tokens_equal(
            lexer.token(),
            NewlineWrap(16)
        )

        # Variable decl
        self.assert_token_line(
            TokenWrap("NAME", "x", 20, 1), TokenWrap("COLON", ":", 20, 2),
            TokenWrap("NAME", "int", 20, 4)
        )

        # Var decl array
        self.assert_token_line(
            TokenWrap("NAME", "x", 21, 1), TokenWrap("COLON", ":", 21, 2),
            TokenWrap("NAME", "int", 21, 4), TokenWrap("LBRACKET", "[", 21, 7),
            TokenWrap("INT", 3, 21, 8), TokenWrap("RBRACKET", "]", 21, 9)
        )

        self.skip_line(3)

        # Var decl with multiple single line comments next to it
        self.assert_token_line(
            TokenWrap("NAME", "x", 25, 1), TokenWrap("COLON", ":", 25, 2),
            TokenWrap("NAME", "int", 25, 4), TokenWrap("LBRACKET", "[", 25, 7),
            TokenWrap("INT", 3, 25, 8), TokenWrap("RBRACKET", "]", 25, 9),
            TokenWrap("LBRACKET", "[", 25, 10), TokenWrap("RBRACKET", "]", 25, 11),
        )

        # Next vardecl
        self.assert_token_line(
            TokenWrap("NAME", "x", 28, 1), TokenWrap("COLON", ":", 28, 2),
            TokenWrap("NAME", "int", 28, 4),
            TokenWrap("LBRACKET", "[", 28, 7), TokenWrap("RBRACKET", "]", 28, 8),
            TokenWrap("LBRACKET", "[", 28, 9), TokenWrap("INT", 3, 28, 10), TokenWrap("RBRACKET", "]", 28, 11),
        )

        #tok = lexer.token()
        #print(tok, TokenWrap.from_lex_token(tok))
        #raise RuntimeError


if __name__ == "__main__":
    unittest.main()
