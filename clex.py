import ply.lex as lex


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
    tok.lexpos = -1
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
        "class": "CLASS",
        "pass": "PASS",

        # Control flow
        "if": "IF",
        "else": "ELSE",
        "elif": "ELIF",
        "while": "WHILE",
        "dowhile": "DOWHILE",
        "switch": "SWITCH",
        "case": "CASE",
        "return": "RETURN",
        "break": "BREAK",

        # Exprs
        "not": "NOT",

        # Macros
        "define": "DEFINE",
        "include": "INCLUDE",
        "ifndef": "IFNDEF",
        "endif": "ENDIF",

        # Types
        "enum": "ENUM",
        "struct": "STRUCT",
        "typedef": "TYPEDEF",

        # Operators
        "and": "AND",
        "or": "OR",

        # Constants
        "NULL": "NULL",
    }

    tokens = (
        'NAME',

        # Literals
        'INT', "FLOAT", 'STRING', "CHAR",

        # Container chars
        # ( ) [ ] { }
        'LPAR', 'RPAR', "LBRACKET", "RBRACKET", "LBRACE", "RBRACE",

        # Binary ops
        # % << >>
        "MOD", "LSHIFT", "RSHIFT",

        # Comparison bin ops
        # LT and GT are also used for casts
        # == != < >
        "EQ", "NE", "LT", "GT", "LE", "GE",

        # Unary ops
        # ++ -- & ~
        "INC", "DEC", "AMP", "INV",

        # Fictitious tokens
        "CAST", "PREINC", "PREDEC", "POSTINC", "POSTDEC", "ADDROF",
        "BITAND", "BITOR", "XOR", "DEREF", "UADD", "USUB",

        'ASSIGN',
        "ARROW",
        "PERIOD",
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

        # Misc
        'COLON', "CARROT", "PIPE",
    ) + tuple(RESERVED.values())

    # This line is necessary until the version of ply that comes out contains the
    # change at:
    # https://github.com/dabeaz/ply/commit/cbef61c58f8b1b3b5e2fc3c2414bcac4303538ce
    # If this line is not included, the parsetab.py module will regenerate
    # every time this is run b/c the signature/hash used to determine if one is
    # generated is a string joining of these tokens, whose order can vary based
    # on the random ordering of keys in the dictionary of reserved words.
    # This line preserves that order.
    tokens = sorted(tokens)

    # Bin ops
    t_MOD = r"\%"
    t_AND = r"and"
    t_OR = r"or"
    t_LSHIFT = r"<<"
    t_RSHIFT = r">>"

    # Comparison ops
    t_LE = r"<="
    t_GE = r">="

    # Unary ops
    t_INC = r"\+\+"
    t_DEC = r"--"
    t_AMP = r"\&"
    t_INV = r"~"

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
    t_PERIOD = r"\."

    t_NULL = r"NULL"

    t_PIPE = r"\|"
    t_CARROT = r"\^"
    t_ELLIPSIS = r"\.\.\."


    ########## Lexer interface #########

    def __init__(self, **kwargs):
        # This is required b/c tracking in the parser requires that the lineno
        # of this lexer be accessed as a property, but I can only return the
        # property from the internal lexer which also requires the property
        # of the outer lexer (passed through module=self), but self.__lexer
        # has not been defined yet.
        self.__initialized = False

        self.__token_stream = None
        self.__paren_count = 0
        self.__bracket_count = 0
        self.__brace_count = 0
        self.__lexer = lex.lex(module=self, **kwargs)
        self.__last_tok = None
        self.__tok_buff = None

        self.__initialized = True

    def input(self, s):
        self.__lexer.input(s)
        self.__token_stream = self.__token_filters()

    def lexpos(self):
        return self.__lexer.lexpos

    @property
    def lineno(self):
        if self.__initialized:
            return self.__lexer.lineno
        return None

    def token(self):
        try:
            self.__last_tok = self.__tok_buff
            tok = next(self.__token_stream)

            # Not all tokens for some reason have a reference to the lexer
            tok.lexer = self.__lexer

            self.__tok_buff = tok
            return tok
        except StopIteration:
            return None

    def last_tok(self):
        return self.__last_tok

    def __iter__(self):
        if self.__token_stream is not None:
            yield from self.__token_stream
        else:
            raise StopIteration

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
        r'\d+(?!\d*\.)'
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
        t.lexer.lineno += t.value.count("\n")
        return t

    def t_CHAR(self, t):
        r"('[^\\]')|('\\[^\\]')"
        t.value = t.value[1:-1]
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

    def t_error(self, t):
        raise SyntaxError("Unknown symbol '{}' at ({}, {})".format(
            t.value[0], t.lineno, find_column(t)
        ))


def find_column(token):
    if token.type == "NEWLINE":
        offset = 0
    else:
        offset = 1
    last_cr = token.lexer.lexdata.rfind('\n', 0, token.lexpos + offset)
    if last_cr < 0:
        last_cr = 0
    column = token.lexpos - last_cr
    return column
