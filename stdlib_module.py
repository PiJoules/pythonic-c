from lang_types import *


STDLIB_MODULE = Module([
    Ifndef("_STDLIB_H"),
    Define("_STDLIB_H"),

    TypeDefStmt(NameType("uint"), "size_t"),

    FuncDecl(
        "malloc",
        [
            VarDecl("size", NameType("size_t")),
        ],
        NameType("void")
    ),

    FuncDecl(
        "free",
        [
            VarDecl("ptr", Pointer(NameType("void"))),
        ],
        NameType("void")
    ),

    FuncDecl(
        "exit",
        [
            VarDecl("status", NameType("void")),
        ],
        NameType("void")
    ),

    Endif(),
])


STDLIB_VARS = dict.fromkeys(
    {
        "malloc",
        "free",
        "exit",
    },
    ("stdlib.h", STDLIB_MODULE)
)

STDLIB_TYPES = dict.fromkeys(
    {
        "size_t",
    },
    ("stdlib.h", STDLIB_MODULE)
)
