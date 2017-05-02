from ply import lex

##### Lexer ######

RESERVED = {
    "def": "DEF",
    "if": "IF",
    "return": "RETURN",
    "define": "DEFINE",
    "include": "INCLUDE",
    "includel": "INCLUDE_LOCAL",
    "enum": "ENUM",
}

tokens = (
    'NAME',

    # Literals
    'INT', "FLOAT", 'STRING',

    # ( ) [ ] { }
    'LPAR', 'RPAR', "LBRACKET", "RBRACKET", "LBRACE", "RBRACE",

    'COLON',
    'EQ',
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
) + tuple(RESERVED.values())


def t_INT(t):
    r'\d+(?!\.)'
    t.value = int(t.value)
    return t

# TODO: Add other floating point representations
def t_FLOAT(t):
    r"\d+\.\d+"
    t.value = float(t.value)
    return t


double_quote = r'"(.*?)(?<!\\)"'
multiline_double = r'"""([\w\W]*?)"""'
str_token = (
    r"(" + multiline_double + r")|" +
    r"(" + double_quote + r")"
)

@lex.TOKEN(str_token)
def t_STRING(t):
    s = t.value
    if s.startswith('"""'):
        t.value = s[3:-3]
    else:
        t.value = s[1:-1]
    return t


t_COLON = r':'
t_EQ = r'=='
t_ASSIGN = r'='
t_LT = r'<'
t_GT = r'>'
t_PLUS = r'\+'
t_MINUS = r'-'
t_MULT = r'\*'
t_DIV = r'/'
t_COMMA = r','
t_ARROW = r"->"

t_LBRACE = r"\{"
t_RBRACE = r"\}"

# Ply nicely documented how to do this.



def t_NAME(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = RESERVED.get(t.value, "NAME")
    return t

# Putting this before t_WS let it consume lines with only comments in
# them so the latter code never sees the WS part.  Not consuming the
# newline.  Needed for "if 1: #comment"


def t_comment(t):
    r"[ ]*\043[^\n]*"  # \043 is '#'
    pass


# Whitespace
def t_WS(t):
    r'[ ]+'
    if t.lexer.at_line_start and empty_container(t.lexer):
        return t

# Don't generate newline tokens when inside of parenthesis, eg
#   a = (1,
#        2, 3)


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.type = "NEWLINE"
    if empty_container(t.lexer):
        return t

def t_LBRACKET(t):
    r"\["
    t.lexer.bracket_count += 1
    return t

def t_RBRACKET(t):
    r"\]"
    t.lexer.bracket_count -= 1
    return t

def t_LPAR(t):
    r'\('
    t.lexer.paren_count += 1
    return t


def t_RPAR(t):
    r'\)'
    # check for underflow?  should be the job of the parser
    t.lexer.paren_count -= 1
    return t


def find_column(input, token):
    last_cr = input.rfind('\n',0,token.lexpos)
    if last_cr < 0:
        last_cr = 0
    column = (token.lexpos - last_cr) + 1
    return column


def t_error(t):
    raise SyntaxError("Unknown symbol '{}' at ({}, {})".format(
        t.value[0], t.lineno, find_column(t.value, t)
    ))

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
NO_INDENT = 0
MAY_INDENT = 1
MUST_INDENT = 2

# only care about whitespace at the start of a line


def track_tokens_filter(lexer, tokens):
    lexer.at_line_start = at_line_start = True
    indent = NO_INDENT
    saw_colon = False
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


def _new_token(type, lineno):
    tok = lex.LexToken()
    tok.type = type
    tok.value = None
    tok.lineno = lineno
    return tok

# Synthesize a DEDENT tag


def DEDENT(lineno):
    return _new_token("DEDENT", lineno)

# Synthesize an INDENT tag


def INDENT(lineno):
    return _new_token("INDENT", lineno)


# Track the indentation level and emit the right INDENT / DEDENT events.
def indentation_filter(tokens):
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
            yield INDENT(token.lineno)

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
                    yield DEDENT(token.lineno)
                    levels.pop()

        yield token

    ### Finished processing ###

    # Must dedent any remaining levels
    if len(levels) > 1:
        assert token is not None
        for _ in range(1, len(levels)):
            yield DEDENT(token.lineno)


# The top-level filter adds an ENDMARKER, if requested.
# Python's grammar uses it.
def filter(lexer):
    token = None
    tokens = iter(lexer.token, None)
    tokens = track_tokens_filter(lexer, tokens)
    for token in indentation_filter(tokens):
        yield token

# Combine Ply and my filters into a new lexer

def empty_container(lexer):
    return (
        (not lexer.paren_count) and
        (not lexer.bracket_count)
    )


class IndentLexer(object):

    def __init__(self, **kwargs):
        self.lexer = lex.lex(**kwargs)
        self.token_stream = None

    def input(self, s):
        self.lexer.input(s)
        self.lexer.paren_count = 0
        self.lexer.bracket_count = 0
        self.token_stream = filter(self.lexer)

    def token(self):
        try:
            return next(self.token_stream)
        except StopIteration:
            return None
