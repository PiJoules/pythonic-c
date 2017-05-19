from lang_ast import *
from cparse import Parser
from file_locs import FAKE_LANG_HEADERS_DIR

import os


class LangType(SlottedClass):
    __slots__ = ("name", )
    __types__ = {
        "name": str,
    }

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name


class PointerType(LangType):
    __slots__ = LangType.__slots__ + ("contents", )
    __types__ = merge_dicts(LangType.__types__, {
        "contents": LangType,
    })

    def __init__(self, *args, **kwargs):
        super().__init__("pointer", *args, **kwargs)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, NullType):
            return True

        return super().__eq__(other)


class NumericTypeMixin:
    pass


class NullType(LangType, NumericTypeMixin):
    def __init__(self, *args, **kwargs):
        super().__init__("NULL", *args, **kwargs)

    def __eq__(self, other):
        return isinstance(other, (PointerType, NullType))

    def __hash__(self):
        return hash(self.name)


class IntType(LangType, NumericTypeMixin):
    def __init__(self, *args, **kwargs):
        super().__init__("int", *args, **kwargs)

    def __eq__(self, other):
        return isinstance(other, NumericTypeMixin)

    def __hash__(self):
        return hash(self.name)


class UIntType(LangType, NumericTypeMixin):
    def __init__(self, *args, **kwargs):
        super().__init__("uint", *args, **kwargs)

    def __eq__(self, other):
        return isinstance(other, NumericTypeMixin)

    def __hash__(self):
        return hash(self.name)


INIT_TYPES = {
    IntType(),
    UIntType(),
    LangType("float"),
    LangType("void"),
    LangType("char"),
    NullType(),
}
BUILTIN_TYPES = {t.name: t for t in INIT_TYPES}


class StructType(LangType):
    __slots__ = LangType.__slots__ + ("members", )
    __types__ = merge_dicts(LangType.__types__, {
        "members": {str: LangType}
    })
    __defaults__ = {
        "members": {}
    }


class CallableType(LangType):
    __slots__ = LangType.__slots__ + ("args", "returns")
    __types__ = merge_dicts(LangType.__types__, {
        "args": [LangType],
        "returns": LangType
    })

    def __init__(self, *args, **kwargs):
        super().__init__("callable", *args, **kwargs)



class Inferer:
    ######### Interface ########

    def __init__(self, *, init_variables=None, init_types=INIT_TYPES,
                 init_typedefs=None,
                 source_dir=None, parent=None,
                 include_dirs=None,
                 call_stack=None):
        self.__variables = init_variables or {}
        self.__types = init_types or set()
        self.__typedefs = init_typedefs or {}
        self.__source_dir = source_dir or os.getcwd()
        self.__include_dirs = (include_dirs or set()) | {FAKE_LANG_HEADERS_DIR}
        self.__parent = parent
        self.__call_stack = call_stack or []

    def variables(self):
        return self.__variables

    def types(self):
        return self.__types

    def bind(self, varname, type):
        self.assert_type_exists(type)
        if varname in self.__variables:
            assert self.__variables[varname] == type
        else:
            self.__variables[varname] = type

    def lookup(self, varname):
        type = self.__variables.get(varname, None)
        if type is not None:
            return type
        elif self.__parent:
            return self.__parent.lookup(varname)

        raise KeyError("Undeclared variable '{}'".format(varname))

    def knowsvar(self, varname):
        """Checks if this environment knows of the variable provided."""
        try:
            self.lookup(varname)
        except KeyError:
            return False
        else:
            return True

    def assert_type_exists(self, t):
        assert isinstance(t, LangType)

        if isinstance(t, PointerType):
            self.assert_type_exists(t.contents)
        elif t not in self.types():
            raise RuntimeError("Type '{}' not previously declared.".format(t))

    def add_type(self, t):
        assert isinstance(t, LangType)
        self.__types.add(t)

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
        parser = Parser()
        with open(path, "r") as f:
            module_ast = parser.parse(f.read())
            self.check(module_ast)

    ####### Type handling ###########

    def bind_type(self, typename, base_t):
        self.assert_type_exists(base_t)
        assert isinstance(typename, str)

        if typename in self.__typedefs:
            raise RuntimeError("{} already typedef'd to {}".format(base_t, typename))
        else:
            self.__typedefs[typename] = base_t

    def node_to_type(self, node):
        assert isinstance(node, LANG_TYPES)

        if isinstance(node, FuncType):
            param_nodes = node.params
            return_node = node.returns

            return CallableType(
                [self.node_to_type(p) for p in param_nodes],
                self.node_to_type(return_node)
            )
        elif isinstance(node, str):
            # Account for typedefs
            if node in self.__typedefs:
                return self.__typedefs[node]
            elif node in BUILTIN_TYPES:
                return BUILTIN_TYPES[node]
            else:
                raise RuntimeError("type for name '{}' not previously declared".format(node))
        elif isinstance(node, Pointer):
            return PointerType(self.node_to_type(node.contents))
        elif isinstance(node, Struct):
            return StructType(node.name)
        else:
            raise RuntimeError("Logic for converting node {} to LangType not implemented".format(type(node)))

    def type_to_node(self, t):
        assert isinstance(t, LangType)

        if isinstance(t, PointerType):
            return Pointer(self.type_to_node(t.contents))
        elif isinstance(t, StructType):
            return t.name
        elif type(t) == LangType:
            return t.name
        else:
            raise RuntimeError("Logic for converting type {} to Node not implemented".format(type(t)))

    ######## Type inference ###########

    def infer(self, node):
        return self.__call_node_method(node, "infer", expected=LangType)

    def infer_Cast(self, node):
        t = self.node_to_type(node.target_type)
        self.assert_type_exists(t)
        return t

    def infer_Call(self, node):
        func = node.func

        if isinstance(func, Name):
            return self.lookup(func.id).returns
        else:
            raise NotImplementedError("No logic yet implemented for inferring type for node {}".format(type(func)))

    def infer_Int(self, node):
        return IntType()

    def infer_Name(self, node):
        return self.lookup(node.id)

    def infer_Null(self, node):
        return NullType()


    ######## Node checking ###########

    def check(self, node):
        return self.__call_node_method(node, "check", expected=(Node, list))

    def check_Define(self, node):
        if node.value:
            expected_t = self.infer(node.value)
            if node.type:
                assert expected_t == node.type
            self.bind(node.name, node.type)
        return Define(
            node.name,
            node.value,
            node.type
        )

    def check_StructDecl(self, node):
        # Check struct members
        struct_t = self.node_to_type(node.struct)

        self.add_type(struct_t)
        self.bind_type(node.struct.name, struct_t)
        struct_t.members = {d.name: self.node_to_type(d.type) for d in node.struct.decls}

        for t in struct_t.members.values():
            self.assert_type_exists(t)
        return node

    def check_FuncDecl(self, node):
        func_t = self.node_to_type(node.type())
        self.assert_type_exists(func_t.returns)
        for param in func_t.args:
            self.assert_type_exists(param)

        self.add_type(func_t)
        self.bind(node.name, func_t)
        return node

    def check_IncludeLocal(self, node):
        path = os.path.join(self.__source_dir, node.path.s)
        self.__check_module_path(path)
        return node

    def check_Include(self, node):
        path = node.path.s
        possible_files = (os.path.join(h, path) for h in self.__include_dirs)

        for f in possible_files:
            if os.path.isfile(f):
                self.__check_module_path(f)
                break
        else:
            raise RuntimeError("File '{}' not found".format(path))

        return node

    def check_FuncDef(self, node):
        name = node.name

        # Check the function signiature
        node_params = node.params
        returns = node.returns
        if name in self.variables():
            # Func was previously declared
            # Check and match parameters and types
            expected_func_t = self.lookup(name)

            assert isinstance(expected_func_t, CallableType)

            if len(node.params) != len(expected_func_t.args):
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
            returns = expected_returns
        else:
            # First instance of function
            # Will need to perform type inference when calling function
            pass

        # Check the body
        body = self.check(node.body)
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
            if expected_t != right_t:
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
        self.bind_type(node.name, base_t)
        return node

    def check_ExprStmt(self, node):
        self.infer(node.value)
        return node

    def check_VarDecl(self, node):
        node_t = self.node_to_type(node.type)

        self.assert_type_exists(node_t)
        name = node.name
        init = node.init

        # Make sure the variable is not declared in the same scope
        if name in self.__variables:
            raise RuntimeError("Cannot declare variable '{}' again in same scope".format(name))

        # Check types
        init_t = self.infer(init)
        if init_t != node_t:
            raise TypeError("Expected type {} for {}. Found {}.".format(node_t, name, init_t))

        # Add variable
        self.bind(name, node_t)
        return node

    def check_VarDeclStmt(self, node):
        return VarDeclStmt(self.check(node.decl))

    def check_list(self, seq):
        return [self.check(n) for n in seq]

    def check_Module(self, node):
        return Module(self.check(node.body))
