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


class TestLineColNo(unittest.TestCase):
    def assert_tokens_equal(self, lex_token, token_wrap):
        assert isinstance(lex_token, lex.LexToken)
        assert isinstance(token_wrap, TokenWrap)

        found = TokenWrap.from_lex_token(lex_token)

        assert found == token_wrap, "Found {}. Expected {}.".format(found, token_wrap)

    def test_alignment_example(self):
        with open("examples/alignment_test.cu", "r") as f:
            code = f.read()

        lexer = Lexer()
        lexer.input(code)

        # First quote
        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("STRING", "double quote comment", 3, 1)
        )

        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("NEWLINE", "\n\n", 3, 23)
        )

        # Multiline string
        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("STRING", "\nmultiline\ndouble\nquotes\n", 5, 1)
        )

        self.assert_tokens_equal(
            lexer.token(),
            TokenWrap("NEWLINE", "\n\n\n", 9, 4)
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
            TokenWrap("NEWLINE", "\n", 12, 16)
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
            TokenWrap("NEWLINE", "\n\n", 13, 26)
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
            TokenWrap("NEWLINE", "\n", 15, 45)
        )

        # Include local

        #tok = lexer.token()
        #print(tok, TokenWrap.from_lex_token(tok))
        #raise RuntimeError


if __name__ == "__main__":
    unittest.main()
