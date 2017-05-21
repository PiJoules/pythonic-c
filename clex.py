from ply import lex


##### Helper functions ##########

def _make_str_regex():
    double_quote = r'"(.*?)(?<!\\)"'
    multiline_double = r'"""([\w\W]*?)"""'
    str_regex = (
        r"(" + multiline_double + r")|" +
        r"(" + double_quote + r")"
    )
    return str_regex


def _new_token(type, lineno):
    tok = lex.LexToken()
    tok.type = type
    tok.value = None
    tok.lineno = lineno
    return tok


def _dedent(lineno):
    # Synthesize a DEDENT tag
    return _new_token("DEDENT", lineno)


def _indent(lineno):
    # Synthesize an INDENT tag
    return _new_token("INDENT", lineno)


class Lexer:
    ######## Token definitions ##########

    RESERVED = {
        "def": "DEF",
        "pass": "PASS",

        # Control flow
        "if": "IF",
        "else": "ELSE",
        "elif": "ELIF",
        "while": "WHILE",
        "do": "DO",
        "switch": "SWITCH",
        "case": "CASE",
        "return": "RETURN",
        "break": "BREAK",

        # Exprs
        "not": "NOT",

        # Macros
        "define": "DEFINE",
        "include": "INCLUDE",
        "includel": "INCLUDE_LOCAL",
        "ifndef": "IFNDEF",
        "endif": "ENDIF",

        # Types
        "enum": "ENUM",
        "struct": "STRUCT",
        "typedef": "TYPEDEF",

        # Constants
        "NULL": "NULL",
    }

    tokens = (
        'NAME',

        # Literals
        'INT', "FLOAT", 'STRING',

        # ( ) [ ] { }
        'LPAR', 'RPAR', "LBRACKET", "RBRACKET", "LBRACE", "RBRACE",

        'COLON',

        # Binary ops
        'EQ', "NE",

        # Unary ops
        "INC", "DEC",

        'ASSIGN',
        "ARROW",
        'LT',
        'GT',
        'PLUS',
        'MINUS',
        'MULT',
        'DIV',
        'WS',
        'NEWLINE',
        'COMMA',
        'INDENT',
        'DEDENT',
        "ELLIPSIS",
    ) + tuple(RESERVED.values())

    t_COLON = r':'
    t_EQ = r'=='
    t_NE = r"!="
    t_ASSIGN = r'='
    t_LT = r'<'
    t_GT = r'>'
    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_MULT = r'\*'
    t_DIV = r'/'
    t_COMMA = r','
    t_ARROW = r"->"

    t_NULL = r"NULL"

    t_INC = r"\+\+"
    t_DEC = r"--"

    t_ELLIPSIS = r"\.\.\."


    ########## Lexer interface #########

    def __init__(self, **kwargs):
        self.__token_stream = None
        self.__paren_count = 0
        self.__bracket_count = 0
        self.__brace_count = 0
        self.__lexer = lex.lex(module=self, **kwargs)

    def input(self, s):
        self.__lexer.input(s)
        self.__token_stream = self.__token_filters()

    def base_lexer(self):
        return self.__lexer

    def token(self):
        try:
            return next(self.__token_stream)
        except StopIteration:
            return None

    def __token_filters(self):
        """
        Apply different filters for postprocessing on the existing
        token stream.
        """
        yield from self.__indent_filter(
            self.__track_tokens_filter(
                iter(self.__lexer.token, None)
            )
        )

    def __indent_filter(self, tokens):
        # Track the indentation level and emit the right INDENT / DEDENT events.
        # A stack of indentation levels; will never pop item 0
        levels = [0]
        token = None
        depth = 0
        prev_was_ws = False
        for token in tokens:
            # if 1:
            # print "Process", token,
            # if token.at_line_start:
            # print "at_line_start",
            # if token.must_indent:
            # print "must_indent",
            # print

            # WS only occurs at the start of the line
            # There may be WS followed by NEWLINE so
            # only track the depth here.  Don't indent/dedent
            # until there's something real.
            if token.type == "WS":
                assert depth == 0
                depth = len(token.value)
                prev_was_ws = True
                # WS tokens are never passed to the parser
                continue

            if token.type == "NEWLINE":
                depth = 0
                if prev_was_ws or token.at_line_start:
                    # ignore blank lines
                    continue
                # pass the other cases on through
                yield token
                continue

            # then it must be a real token (not WS, not NEWLINE)
            # which can affect the indentation level

            prev_was_ws = False
            if token.must_indent:
                # The current depth must be larger than the previous level
                if not (depth > levels[-1]):
                    raise IndentationError("expected an indented block")

                levels.append(depth)
                yield _indent(token.lineno)

            elif token.at_line_start:
                # Must be on the same level or one of the previous levels
                if depth == levels[-1]:
                    # At the same level
                    pass
                elif depth > levels[-1]:
                    raise IndentationError(
                        "indentation increase but not in new block")
                else:
                    # Back up; but only if it matches a previous level
                    try:
                        i = levels.index(depth)
                    except ValueError:
                        raise IndentationError("inconsistent indentation")
                    for _ in range(i + 1, len(levels)):
                        yield _dedent(token.lineno)
                        levels.pop()

            yield token

        ### Finished processing ###

        # Must dedent any remaining levels
        if len(levels) > 1:
            assert token is not None
            for _ in range(1, len(levels)):
                yield _dedent(token.lineno)

    def __track_tokens_filter(self, tokens):
        # I implemented INDENT / DEDENT generation as a post-processing filter

        # The original lex token stream contains WS and NEWLINE characters.
        # WS will only occur before any other tokens on a line.

        # I have three filters.  One tags tokens by adding two attributes.
        # "must_indent" is True if the token must be indented from the
        # previous code.  The other is "at_line_start" which is True for WS
        # and the first non-WS/non-NEWLINE on a line.  It flags the check so
        # see if the new line has changed indication level.

        # Python's syntax has three INDENT states
        #  0) no colon hence no need to indent
        #  1) "if 1: go()" - simple statements have a COLON but no need for an indent
        #  2) "if 1:\n  go()" - complex statements have a COLON NEWLINE and must indent

        # only care about whitespace at the start of a line

        NO_INDENT = 0
        MAY_INDENT = 1
        MUST_INDENT = 2

        # only care about whitespace at the start of a line
        lexer = self.__lexer
        lexer.at_line_start = at_line_start = True
        indent = NO_INDENT
        for token in tokens:
            token.at_line_start = at_line_start

            if token.type == "COLON":
                at_line_start = False
                indent = MAY_INDENT
                token.must_indent = False

            elif token.type == "NEWLINE":
                at_line_start = True
                if indent == MAY_INDENT:
                    indent = MUST_INDENT
                token.must_indent = False

            elif token.type == "WS":
                assert token.at_line_start == True
                at_line_start = True
                token.must_indent = False

            else:
                # A real token; only indent after COLON NEWLINE
                if indent == MUST_INDENT:
                    token.must_indent = True
                else:
                    token.must_indent = False
                at_line_start = False
                indent = NO_INDENT

            yield token
            lexer.at_line_start = at_line_start

    def is_outside_brackets(self):
        """Returns if the current token is inside a set of brackets."""
        return (
            (not self.__paren_count) and
            (not self.__bracket_count) and
            (not self.__brace_count)
        )


    ########### Token handlers ############

    def t_INT(self, t):
        r'\d+(?!\.)'
        t.value = int(t.value)
        return t

    # TODO: Add other floating point representations
    def t_FLOAT(self, t):
        r"\d+\.\d+"
        t.value = float(t.value)
        return t

    @lex.TOKEN(_make_str_regex())
    def t_STRING(self, t):
        s = t.value
        if s.startswith('"""'):
            t.value = s[3:-3]
        else:
            t.value = s[1:-1]
        return t

    def t_NAME(self, t):
        r'[a-zA-Z_][a-zA-Z0-9_]*'
        t.type = self.RESERVED.get(t.value, "NAME")
        return t

    def t_comment(self, t):
        r"[ ]*\#[^\n]*"
        pass

    # Whitespace
    def t_WS(self, t):
        r'[ ]+'
        if t.lexer.at_line_start and self.is_outside_brackets():
            return t

    # Don't generate newline tokens when inside of parenthesis, eg
    #   a = (1,
    #        2, 3)

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)
        t.type = "NEWLINE"
        if self.is_outside_brackets():
            return t

    def t_LBRACKET(self, t):
        r"\["
        self.__bracket_count += 1
        return t

    def t_RBRACKET(self, t):
        r"\]"
        self.__bracket_count -= 1
        return t

    def t_LPAR(self, t):
        r'\('
        self.__paren_count += 1
        return t

    def t_RPAR(self, t):
        r'\)'
        self.__paren_count -= 1
        return t

    def t_LBRACE(self, t):
        r"\{"
        self.__brace_count += 1
        return t

    def t_RBRACE(self, t):
        r"\}"
        self.__brace_count -= 1
        return t

    def find_column(self, input, token):
        last_cr = input.rfind('\n',0,token.lexpos)
        if last_cr < 0:
            last_cr = 0
        column = (token.lexpos - last_cr) + 1
        return column


    def t_error(self, t):
        raise SyntaxError("Unknown symbol '{}' at ({}, {})".format(
            t.value[0], t.lineno, self.find_column(t.value, t)
        ))
