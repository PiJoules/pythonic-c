LANG_HEADER_EXT = ".hcu"
LANG_SOURCE_EXT = ".cu"


def is_c_header(source):
    return source.endswith(".h")


def is_c_source(source):
    return source.endswith(".c")


def is_lang_source(source):
    return source.endswith(LANG_SOURCE_EXT)


def to_c_source(source):
    if source.endswith(LANG_HEADER_EXT):
        return source[:-len(LANG_HEADER_EXT)] + ".h"
    elif source.endswith(LANG_SOURCE_EXT):
        return source[:-len(LANG_SOURCE_EXT)] + ".c"
    elif source.endswith(".h"):
        # To enable using C headers
        return source
    else:
        raise RuntimeError("Unknown file type '{}'".format(source))
