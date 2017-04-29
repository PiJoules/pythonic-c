import ply.lex as lex


reserved = {
    "def": "DEF",
}


tokens = (
    "LPAREN", "RPAREN",

    "NEWLINE",

    "ID",
) + tuple(reserved.values())


t_LPAREN = r"\("
t_RPAREN = r"\)"


def t_ID(t):
    r"[a-zA-Z_][a-zA-Z0-9_]*"
    t.type = RESERVED.get(t.value, "NAME")
    return t


def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)
    t.type = "NEWLINE"
    return t


def t_error(t):
    raise RuntimeError("No token implemented for {}".format(t))


LEXER = lex.lex()
