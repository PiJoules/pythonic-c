from lang_types import *


ASSERT_MODULE = Module([
    Ifndef("_ASSERT_H"),
    Define("_ASSERT_H"),

    FuncDecl(
        "assert",
        [
            VarDecl("expr", "int"),
        ],
        "void"
    ),

    Endif(),
])


ASSERT_VARS = dict.fromkeys(
    {
        "assert",
    },
    ("assert.h", ASSERT_MODULE)
)
