from lang_types import *


STDLIB_MODULE = Module([
    Ifndef("_STDLIB_H"),
    Define("_STDLIB_H"),

    TypeDefStmt("uint", "size_t"),

    FuncDecl(
        "malloc",
        [
            VarDecl("size", "size_t"),
        ],
        "void"
    ),

    FuncDecl(
        "free",
        [
            VarDecl("ptr", Pointer("void")),
        ],
        "void"
    ),

    Endif(),
])


STDLIB_VARS = dict.fromkeys(
    {
        "malloc",
        "free",
    },
    ("stdlib.h", STDLIB_MODULE)
)

STDLIB_TYPES = dict.fromkeys(
    {
        "size_t",
    },
    ("stdlib.h", STDLIB_MODULE)
)
