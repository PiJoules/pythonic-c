from .stdio_module import STDIO_VARS
from .stdlib_module import STDLIB_VARS, STDLIB_TYPES
from .assert_module import ASSERT_VARS
from .string_module import STRING_VARS, STRING_TYPES


C_VARS = {}
C_VARS.update(STDIO_VARS)
C_VARS.update(STDLIB_VARS)
C_VARS.update(ASSERT_VARS)
C_VARS.update(STRING_VARS)


C_TYPES = {}
C_TYPES.update(STDLIB_TYPES)
C_TYPES.update(STRING_TYPES)
