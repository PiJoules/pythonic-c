from .stdio_module import STDIO_VARS
from .stdlib_module import STDLIB_VARS, STDLIB_TYPES
from .assert_module import ASSERT_VARS


BUILTIN_VARS = {}
BUILTIN_VARS.update(STDIO_VARS)
BUILTIN_VARS.update(STDLIB_VARS)
BUILTIN_VARS.update(ASSERT_VARS)


BUILTIN_TYPES = {}
BUILTIN_TYPES.update(STDLIB_TYPES)
