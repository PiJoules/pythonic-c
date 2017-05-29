from lang_ast import *
from cparse import Parser
from lang_types import *

from stdio_module import STDIO_VARS
from stdlib_module import STDLIB_VARS, STDLIB_TYPES
from assert_module import ASSERT_VARS

import os


INIT_TYPES = {
    LangType("char"),
    LangType("short"),
    LangType("int"),
    LangType("long"),

    # Unsigned
    LangType("uint"),

    # Floating point
    LangType("float"),
    LangType("double"),

    # Misc
    NullType(),
    LangType("void"),
    VarargType(),
}


BUILTIN_TYPES = {t.name: t for t in INIT_TYPES}


BUILTIN_VARS = {}
BUILTIN_VARS.update(STDIO_VARS)
BUILTIN_VARS.update(STDLIB_VARS)
BUILTIN_VARS.update(ASSERT_VARS)


MODULE_TYPES = {}
MODULE_TYPES.update(STDLIB_TYPES)


class Inferer:
    ######### Interface ########

    def __init__(self, *, init_variables=None,
                 init_types=None,
                 extra_includes=None,
                 source_file=None,
                 included_files=None,
                 call_stack=None):
        self.__variables = init_variables or {}
        self.__types = init_types or dict.fromkeys(INIT_TYPES)
        self.__call_stack = call_stack or []
        self.__found_included_files = included_files or {}
        self.__extra_includes = extra_includes or set()

        # The frame will change each time a new scope is entered
        self.__frames = []

        self.__init_src_file(source_file)

    def __init_src_file(self, source):
        if source:
            assert os.path.isfile(source)
            self.__source = source
            self.__source_dir = os.path.dirname(source)
        else:
            self.__source = self.__source_dir = None

    def enter_scope(self):
        """
        Called to copy any attributes of the inferer that should not be changed
        when exiting a scope, such as a new function.
        """
        self.__frames.append((
            self.__variables,
            self.__types,
        ))

        self.__variables = dict(self.__variables)
        self.__types = dict(self.__types)

    def exit_scope(self):
        """
        Called to reset the attributes that should bot be edited of the
        previous scope y popping them from the frame.
        """
        frame_attrs = self.__frames.pop()
        self.__variables = frame_attrs[0]
        self.__types = frame_attrs[1]

    def includes(self):
        """Returns a dict mapping all includes found to their type infered asts."""
        return self.__found_included_files

    def variables(self):
        return self.__variables

    def bind(self, varname, type):
        assert isinstance(type, LangType)
        if type.__class__ == LangType:
            self.assert_type_exists(type)

        if varname in self.__variables:
            assert self.__variables[varname] == type
        else:
            self.__variables[varname] = type

    def lookup(self, varname):
        type = self.__variables.get(varname, None)
        if type is not None:
            return type

        raise KeyError("Undeclared variable '{}'".format(varname))

    def knowsvar(self, varname):
        """Checks if this environment knows of the variable provided."""
        try:
            self.lookup(varname)
        except KeyError:
            return False
        else:
            return True

    def type_exists(self, t):
        assert isinstance(t, LangType)
        if isinstance(t, PointerType):
            return self.type_exists(t.contents)
        return t in self.__types

    def assert_type_exists(self, t):
        if not self.type_exists(t):
            raise RuntimeError("Type '{}' not previously declared.".format(t))

    def assert_type_not_exists(self, t):
        if self.type_exists(t):
            self.__dump_call_stack()
            raise RuntimeError("Type '{}' already declared.".format(t))

    def __dump_call_stack(self):
        print("------ Call stack --------")
        for func in self.__call_stack:
            print(func)

    def __call_node_method(self, node, prefix, expected=None):
        name = node.__class__.__name__

        self.__call_stack.append("{}: {}".format(prefix, name))

        method_name = prefix + "_" + name
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            result = method(node)

            if expected is not None and not isinstance(result, expected):
                self.__dump_call_stack()
                raise RuntimeError("Expected {} back from {}(). Got {}.".format(expected, method_name, type(result)))

            self.__call_stack.pop()

            return result
        else:
            self.__dump_call_stack()
            raise RuntimeError("No {} method implemented for node '{}'. Implement {}(self, node) to check this type of node".format(
                prefix,
                name,
                method_name
            ))

    def __check_module_path(self, path):
        """
        Create the module ast, perform type inference on it, then keep track of
        the ast for later use.
        """
        parser = Parser(source_file=path)
        with open(path, "r") as f:
            module_ast = parser.parse(f.read())
            module_ast = self.check(module_ast)

            included_files = self.__found_included_files
            if path not in included_files:
                included_files[path] = module_ast

    def add_extra_c_header(self, header):
        assert header not in self.__extra_includes
        self.__extra_includes.add(header)

    ####### Type handling ###########

    def add_type(self, new_type):
        """
        Add a new base type. This is primarily meant for newly declared
        structs and enums.
        """
        assert isinstance(new_type, LangType)
        if new_type in self.__types:
            raise RuntimeError("{} already previously declared.".format(new_type))
        self.__types[new_type] = None

    def bind_typedef(self, typename, base_t):
        self.assert_type_exists(base_t)
        assert isinstance(typename, LangType)

        if typename in self.__types:
            found = self.__types[typename]
            raise RuntimeError("{}({}) already typedef'd to {}({})".format(
                typename, type(typename),
                found, type(found),
            ))
        else:
            self.__types[typename] = base_t

    def __exhaust_typedef_chain(self, typedef_t):
        """
        Given a LangType, traverse the known types until we hit a value of None,
        indicating the type used as a key is a base type.
        """
        actual_t = self.__types[typedef_t]
        while actual_t is not None:
            # Actual is another typedef
            typedef_t = actual_t
            actual_t = self.__types[typedef_t]
        return typedef_t

    def node_to_type(self, node):
        """Needs to handle
        - TypeMixin nodes
          - NameType
          - Pointer
          - Array
        - Typedefs
          - Function will receieve a NameType
          - Do not keep nodes in a dict since they aren't meant to be hashable
        """

        assert isinstance(node, TypeMixin)

        if isinstance(node, FuncType):
            param_nodes = node.params
            return_node = node.returns

            return CallableType(
                [VarargType() if isinstance(p, Ellipsis) else self.node_to_type(p) for p in param_nodes],
                self.node_to_type(return_node)
            )
        elif isinstance(node, NameType):
            # Account for typedefs
            t = LangType(node.id)
            if t in self.__types:
                # Exhaust any typedef chains
                result = self.__exhaust_typedef_chain(t)
            elif node.id in MODULE_TYPES and t not in self.__types:
                c_header, module = MODULE_TYPES[node.id]
                self.add_extra_c_header(c_header)
                self.__check_module(module)
                result = self.__exhaust_typedef_chain(t)
            else:
                raise RuntimeError("type for name '{}' not previously declared".format(node))
            return result
        elif isinstance(node, Pointer):
            return PointerType(self.node_to_type(node.contents))
        #elif isinstance(node, Struct):
        #    return StructType(node.name)
        else:
            raise RuntimeError("Logic for converting node {} to LangType not implemented".format(type(node)))

    def type_to_node(self, t):
        assert isinstance(t, LangType)

        if isinstance(t, PointerType):
            return Pointer(self.type_to_node(t.contents))
        elif isinstance(t, StructType):
            return NameType(t.name)
        elif type(t) == LangType:
            return NameType(t.name)
        else:
            raise RuntimeError("Logic for converting type {} to Node not implemented".format(type(t)))

    ######## Type inference ###########

    def infer(self, node):
        assert isinstance(node, ValueMixin)
        return self.__call_node_method(node, "infer", expected=LangType)

    def infer_Cast(self, node):
        t = self.node_to_type(node.target_type)
        self.assert_type_exists(t)
        return t

    def infer_Call(self, node):
        func = node.func

        # Check builtin functions
        # Perform if the function is a builtin one and not previously declared
        if isinstance(func, Name) and func.id in BUILTIN_VARS and not self.knowsvar(func.id):
            c_header, module = BUILTIN_VARS[func.id]
            self.add_extra_c_header(c_header)
            self.__check_module(module)

        if isinstance(func, Name):
            return self.lookup(func.id).returns
        else:
            raise NotImplementedError("No logic yet implemented for inferring type for node {}".format(type(func)))

    def infer_Int(self, node):
        return LangType("int")

    def infer_Float(self, node):
        return LangType("float")

    def infer_Name(self, node):
        return self.lookup(node.id)

    def infer_Null(self, node):
        return NullType()

    def infer_StructPointerDeref(self, node):
        value = node.value
        member = node.member
        struct_t = self.infer(value).contents

        if not isinstance(struct_t, StructType):
            raise RuntimeError("Expected {} to be a struct. Found {}.".format(value, struct_t))

        return struct_t.members[member]

    def infer_BinOp(self, node):
        left = node.left
        right = node.right
        op = node.op

        left_t = self.infer(left)
        right_t = self.infer(right)

        def __pointer_offset(ptr_t, offset_t):
            """Return the pointer type if a pointer and whole number are provided."""
            if not isinstance(ptr_t, Pointer):
                raise RuntimeError("Expected the pointer to be a PointerType")
            if not isinstance(offset_t, WholeNumberMixin):
                raise RuntimeError("Expected the offset to be a whole number.")
            return ptr_t

        def __anyinstance(vals, types):
            return any(isinstance(v, types) for v in vals)

        def __dominant_base_type(t1, t2):
            """
            Returns the dominant base type.

            http://stackoverflow.com/a/5563131/2775471
            """
            types = (t1, t2)
            if t1.name == "void" or t2.name == "void":
                raise RuntimeError("Cannot add to void type")
            elif t1.name == "float" or t2.name == "float":
                return LangType("float")
            elif t1.name == "uint" or t2.name == "uint":
                return LangType("uint")
            else:
                return LangType("int")

        if op == "+":
            if isinstance(left_t, Pointer):
                return __pointer_offset(left_t, right_t)
            elif isinstance(right_t, Pointer):
                return __pointer_offset(right_t, left_t)
            else:
                return __dominant_base_type(left_t, right_t)
        else:
            raise RuntimeError("Unable to infer for binary operation '{}'".format(op))

    def infer_PostInc(self, node):
        return self.infer(node.value)

    def infer_PostDec(self, node):
        return self.infer(node.value)

    def infer_Char(self, node):
        return LangType("char")


    ######## Node checking ###########

    def check(self, node):
        return self.__call_node_method(node, "check", expected=(Node, list))

    def check_Define(self, node):
        if node.value:
            expected_t = self.infer(node.value)
            self.bind(node.name, expected_t)

        return Define(
            node.name,
            node.value,
        )

    def check_StructDecl(self, node):
        # Check struct members
        struct_t = StructType(node.struct.name)

        self.add_type(struct_t)
        self.bind_typedef(LangType(node.struct.name), struct_t)
        struct_t.members = {d.name: self.node_to_type(d.type) for d in node.struct.decls}

        for t in struct_t.members.values():
            self.assert_type_exists(t)
        return node

    def check_FuncDecl(self, node):
        func_t = self.node_to_type(node.type())
        self.assert_type_exists(func_t.returns)
        for param in func_t.args:
            self.assert_type_exists(param)

        self.bind(node.name, func_t)
        return node

    def check_Include(self, node):
        path = os.path.join(self.__source_dir, node.path.s)
        self.__check_module_path(path)
        return node

    def _check_and_create_main(self, funcdef):
        """Check the main method and return it."""
        name = funcdef.name
        params = funcdef.params

        if not (len(params) == 0 or len(params) == 2):
            raise RuntimeError("Expected either no or 2 parameters for main function")

        argc_t = NameType("int")
        argv_t = Pointer(Pointer(NameType("char")))

        if params:
            argc, argv = params

            # Check argc
            if not isinstance(argc, VarDecl):
                argc = VarDecl(argc, argc_t)
            else:
                if argc.type != argc_t:
                    raise RuntimeError("Expected type int for first argumenty of main function")
                if argc.init is not None:
                    raise RuntimeError("No initial type expected for first argument of main method")

            # Check argv
            if not isinstance(argv, VarDecl):
                argv = VarDecl(argv, argv_t, None)
            else:
                if argv.type != argv_t:
                    raise RuntimeError("Expected type char** for second argument of main function")
                if argv.init is not None:
                    raise RuntimeError("No initial type expected for second argument of main method")

            params = [argc, argv]

        returns = funcdef.returns
        if returns is None:
            returns = NameType("int")
        elif returns != NameType("int"):
            raise RuntimeError("Expected int return type for main function")

        return FuncDef("main", params, funcdef.body, returns)

    def _assert_args_as_vardecls(self, params):
        """
        Assert that all parameters in a function are variable declarations.
        """
        for param in params:
            assert isinstance(param, VarDecl)

    def check_FuncDef(self, node):
        # Check for main function
        if node.name == "main":
            node = self._check_and_create_main(node)

        name = node.name
        node_params = node.params

        # Check the function signiature
        returns = node.returns
        if name in self.variables():
            # Func was previously declared
            # Check and match parameters and types
            expected_func_t = self.lookup(name)

            assert isinstance(expected_func_t, CallableType)

            if expected_func_t.args and isinstance(expected_func_t.args[-1], VarargType):
                # Check to make sure there is only one varargtype at the end
                # of the arguments list
                if len(expected_func_t.args) == 1:
                    raise RuntimeError("Expected 1 argument before Ellipsis")

                for i in range(len(expected_func_t.args)-1, -1, -1):
                    if isinstance(expected_func_t.args[i], VarargType):
                        raise RuntimeError("Expected only 1 Ellipsis in function")

                if len(node.params) < len(expected_func_t.args) - 1:
                    raise RuntimeError("Function declaration requires at least {} arguments. {} provided.".format(len(expected_func_t.args) - 1, len(node.params)))

            elif len(node.params) != len(expected_func_t.args):
                    raise RuntimeError("Function definition and declaration of '{}' expected to have the same number of arguments".format(name))

            # Check and replace params
            new_node_params = []
            for i, param in enumerate(node.params):
                expected_param_t = expected_func_t.args[i]
                if isinstance(param, str):
                    new_node_params.append(
                        VarDecl(param, self.type_to_node(expected_param_t))
                    )
                elif param.type != expected_func_t.params[i]:
                    raise RuntimeError("Expected {} to be of type {} from previous declaration".format(param.name))
                else:
                    new_node_params.append(param)
            node_params = new_node_params

            # Check and replace returns
            expected_returns = expected_func_t.returns
            if node.returns:
                assert node.returns == expected_returns
            returns = self.type_to_node(expected_returns)
        else:
            # First instance of function
            # TODO: Will need to perform type inference when calling function
            # For now, just make sure the function has variable declarations
            # as its arguments and a return type.
            self._assert_args_as_vardecls(node.params)
            assert isinstance(returns, TypeMixin)

        # Add the params to the scope
        self.enter_scope()
        for param in node_params:
            param_t = self.node_to_type(param.type)
            self.bind(param.name, param_t)
        body = self.check(node.body)
        self.exit_scope()

        # Check the body
        return FuncDef(
            name,
            node_params,
            body,
            returns
        )

    def check_Assign(self, node):
        left = node.left
        right = node.right
        right_t = self.infer(right)

        if isinstance(left, Name):
            name = left.id
            if self.knowsvar(name):
                expected_t = self.lookup(name)
                if expected_t != right_t:
                    raise TypeError("Expected type {} for {}. Found {}.".format(expected_t, name, right_t))
                return node
            else:
                # First instance of this variable
                # Change to a VarDecl
                return self.check(VarDeclStmt(VarDecl(
                    name,
                    self.type_to_node(right_t),
                    right
                )))
        elif isinstance(left, StructPointerDeref):
            # Get the struct and check the member
            value = left.value
            member = left.member

            value_t = self.infer(value)
            expected_t = value_t.contents.members[member]
            if expected_t != right_t and not self.__can_implicit_assign(expected_t, right_t):
                raise TypeError("Expected type {} for member {} of struct {}. Found {}.".format(expected_t, member, value_t.contents.name, right_t))

            return node
        else:
            raise NotImplementedError("Unable to assign to {}".format(type(left)))

    def check_Return(self, node):
        self.infer(node.value)
        return node

    def check_Ifndef(self, node):
        return node

    def check_Endif(self, node):
        return node

    def check_TypeDefStmt(self, node):
        base_t = self.node_to_type(node.type)
        self.assert_type_exists(base_t)
        self.bind_typedef(LangType(node.name), base_t)
        return node

    def check_ExprStmt(self, node):
        self.infer(node.value)
        return node

    def __can_implicit_assign(self, target_t, value_t):
        """Check if the value type can be implicitely converted to the target
        type."""
        return (target_t, value_t) in {
            # To char
            (LangType("char"), LangType("int")),

            # To int
            (LangType("int"), LangType("char")),

            # To uint
            (LangType("uint"), LangType("int")),

            # To double
            (LangType("double"), LangType("float")),
        }

    def check_VarDecl(self, node):
        node_t = self.node_to_type(node.type)

        self.assert_type_exists(node_t)
        name = node.name
        init = node.init

        # Make sure the variable is not declared in the same scope
        if name in self.__variables:
            raise RuntimeError("Cannot declare variable '{}' again in same scope".format(name))

        # Check types
        if init:
            init_t = self.infer(init)
            if init_t != node_t and not self.__can_implicit_assign(node_t, init_t):
                raise TypeError("Expected type {} for {}. Found {}.".format(node_t, name, init_t))

        # Add variable
        self.bind(name, node_t)
        return node

    def check_VarDeclStmt(self, node):
        return VarDeclStmt(self.check(node.decl))

    def check_While(self, node):
        return While(
            self.check(node.test),
            self.check(node.body),
            self.check(node.orelse),
        )

    def check_Compare(self, node):
        return Compare(
            self.check(node.left),
            node.op,
            self.check(node.right),
        )

    def check_StructPointerDeref(self, node):
        return StructPointerDeref(
            self.check(node.value),
            node.member
        )

    def check_Name(self, node):
        return node

    def check_Null(self, node):
        return node

    def check_If(self, node):
        return If(
            self.check(node.test),
            self.check(node.body),
            self.check(node.orelse)
        )

    def check_list(self, seq):
        def __is_string_comment(node):
            return isinstance(node, ExprStmt) and isinstance(node.value, Str)

        return [self.check(n) for n in seq if not __is_string_comment(n)]

    def check_EnumDecl(self, node):
        # Create an enum type
        enum_t = LangType(node.enum.name)
        self.add_type(enum_t)

        for member in node.enum.members:
            self.bind(member, enum_t)

        return node

    def check_Switch(self, node):
        return Switch(
            self.check(node.test),
            self.check(node.cases)
        )

    def check_Case(self, node):
        return Case(
            self.check(node.tests),
            self.check(node.body)
        )

    def check_Break(self, node):
        return node

    def check_Pass(self, node):
        return node

    def check_Default(self, node):
        return Default(
            self.check(node.body)
        )

    def __check_module(self, node, *, is_base_module=False):
        if is_base_module and node.filename:
            self.__init_src_file(node.filename)

        checked_body = self.check(node.body)

        # Add extra includes
        if is_base_module:
            extra_includes = list(map(CInclude, self.__extra_includes))
            checked_body = extra_includes + checked_body

        return Module(checked_body, node.filename)

    def check_Module(self, node):
        return self.__check_module(node, is_base_module=True)
