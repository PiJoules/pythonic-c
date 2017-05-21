LANG_HEADER_EXT = ".hu"
LANG_SOURCE_EXT = ".cu"


def is_c_header(source):
    return source.endswith(".h")


def is_c_source(source):
    return source.endswith(".c")


def is_lang_source(source):
    return source.endswith(LANG_SOURCE_EXT)


def is_lang_header(source):
    return source.endswith(LANG_HEADER_EXT)


def is_lang_file(source):
    return is_lang_source(source) or is_lang_header(source)


def to_c_file(source):
    assert is_lang_file(source)

    if source.endswith(LANG_HEADER_EXT):
        return source[:-len(LANG_HEADER_EXT)] + ".h"
    elif source.endswith(LANG_SOURCE_EXT):
        return source[:-len(LANG_SOURCE_EXT)] + ".c"
    else:
        raise RuntimeError("Unknown file type '{}'".format(source))
