from lang_types import *


STDIO_MODULE = Module([
    Ifndef("_STDIO_H"),
    Define("_STDIO_H"),

    # Variables

    VarDeclStmt(VarDecl("stdin", Pointer(NameType("FILE")))),
    VarDeclStmt(VarDecl("stderr", Pointer(NameType("FILE")))),

    # Functions

    # 22
    FuncDecl(
        "printf",
        [
            VarDecl("format", Pointer(NameType("char"))),
            Ellipsis(),
        ],
        NameType("void")
    ),

    # 27
    FuncDecl(
        "fscanf",
        [
            VarDecl("stream", Pointer(NameType("FILE"))),
            VarDecl("format", Pointer(NameType("char"))),
        ],
        NameType("void")
    ),

    # 33
    FuncDecl(
        "fputs",
        [
            VarDecl("char", Pointer(NameType("char"))),
            VarDecl("stream", Pointer(NameType("FILE"))),
        ],
        NameType("int")
    ),

    Endif(),
])


STDIO_VARS = dict.fromkeys(
    {
        # Variables
        "stdin",
        "stderr",

        # Funcs
        "printf",
        "fscanf",
        "fputs",
    },
    ("stdio.h", STDIO_MODULE)
)
