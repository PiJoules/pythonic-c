from lang_ast import *


INIT_LIBS = {
    "assert.h": Module([
        FuncDecl(
            "assert",
            [VarDecl("expr", "int")],
            "void"
        ),
    ]),

    "stdlib.h": Module([
        # size_t
        TypeDefStmt("uint", "size_t"),

        # malloc()
        FuncDecl(
            "malloc",
            [VarDecl("size", "size_t")],
            Pointer("void")
        ),

        # free()
        FuncDecl(
            "free",
            [VarDecl("ptr", Pointer("void"))],
            "void"
        ),
    ]),
}
