from lang_types import *


ASSERT_MODULE = Module([
    Ifndef("_ASSERT_H"),
    Define("_ASSERT_H"),

    FuncDecl(
        "assert",
        [
            VarDecl("expr", NameType("int")),
        ],
        NameType("void")
    ),

    Endif(),
])


ASSERT_VARS = dict.fromkeys(
    {
        "assert",
    },
    ("assert.h", ASSERT_MODULE)
)
