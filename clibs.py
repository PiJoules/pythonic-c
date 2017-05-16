from lang_ast import *


INIT_LIBS = {
    "stdlib.h": Module([
        # size_t
        TypeDefStmt("uint", "size_t"),

        # malloc()
        FuncDecl(
            "malloc",
            [VarDecl("size", "size_t")],
            Pointer("void")
        )
    ]),
}
