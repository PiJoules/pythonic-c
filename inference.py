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


INIT_TYPES = {
    LangType("int"),
    LangType("uint"),
    LangType("float"),
    LangType("void"),
    LangType("char"),
}


def node_to_type(node):
    assert isinstance(node, LANG_TYPES)

    if isinstance(node, FuncType):
        param_nodes = node.params
        return_node = node.returns

        return CallableType(
            [node_to_type(p) for p in param_nodes],
            node_to_type(return_node)
        )
    elif isinstance(node, str):
        return LangType(node)
    elif isinstance(node, Pointer):
        return PointerType(node_to_type(node.contents))
    elif isinstance(node, Struct):
        return StructType(
            node.name,
            {d.name: node_to_type(d.type) for d in node.decls}
        )
    else:
        raise RuntimeError("Logic for converting node {} to LangType not implemented".format(type(node)))


class StructType(LangType):
    __slots__ = LangType.__slots__ + ("members", )
    __types__ = merge_dicts(LangType.__types__, {
        "members": {str: LangType}
    })

    def __str__(self):
        return "struct {} {{{}}}".format(
            self.name,
            ", ".join("{}:{}".format(k, v) for k, v in self.members)
        )


class CallableType(LangType):
    __slots__ = LangType.__slots__ + ("args", "returns")
    __types__ = merge_dicts(LangType.__types__, {
        "args": [LangType],
        "returns": LangType
    })

    def __init__(self, *args, **kwargs):
        super().__init__("callable", *args, **kwargs)


class PointerType(LangType):
    __slots__ = LangType.__slots__ + ("contents", )
    __types__ = merge_dicts(LangType.__types__, {
        "contents": LangType,
    })

    def __init__(self, *args, **kwargs):
        super().__init__("pointer", *args, **kwargs)



class Inferer:
    ######### Interface ########

    def __init__(self, *, init_variables=None, init_types=INIT_TYPES,
                 source_dir=None, parent=None,
                 include_dirs=None):
        self.__variables = init_variables or {}
        self.__types = init_types or set()
        self.__source_dir = source_dir or os.getcwd()
        self.__include_dirs = (include_dirs or set()) | {FAKE_LANG_HEADERS_DIR}
        self.__parent = parent
        self.__call_stack = []

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

    ######## Type inference ###########

    def infer(self, node):
        return self.__call_node_method(node, "infer", expected=LANG_TYPES)

    def infer_Cast(self, node):
        return node.target_type

    def infer_Call(self, node):
        func = node.func

        if isinstance(func, Name):
            return self.lookup(func.id).returns
        else:
            raise NotImplementedError("No logic yet implemented for inferring type for node {}".format(type(func)))

    def infer_Int(self, node):
        return "int"

    def infer_Name(self, node):
        return self.lookup(node.id)


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
        struct_t = node_to_type(node.struct)
        self.add_type(struct_t)
        for t in struct_t.members.values():
            self.assert_type_exists(t)
        return node

    def check_FuncDecl(self, node):
        func_t = node_to_type(node.type())
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

            assert isinstance(expected_func_t, FuncType)

            if len(node.params) != len(expected_func_t.params):
                raise RuntimeError("Function definition and declaration of '{}' expected to have the same number of arguments".format(name))

            # Check and replace params
            new_node_params = []
            for i, param in enumerate(node.params):
                expected_param_t = expected_func_t.params[i]
                if isinstance(param, str):
                    new_node_params.append(
                        VarDecl(param, expected_param_t)
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

        if isinstance(left, Name):
            name = left.id
            right_t = self.infer(right)
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
                    right_t,
                    right
                )))
        elif isinstance(left, StructPointerDeref):
            # Get the struct and check the member
            value = left.value
            member = left.member

            expected_t = self.infer(value)
            print(type(expected_t))
            raise NotImplementedError
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
        self.add_type(LangType(node.name))
        return node

    def check_ExprStmt(self, node):
        self.infer(node.value)
        return node

    def check_VarDecl(self, node):
        self.assert_type_exists(node.type)
        name = node.name
        init = node.init

        # Make sure the variable is not declared in the same scope
        if name in self.__variables:
            raise RuntimeError("Cannot declare variable '{}' again in same scope".format(name))

        # Check types
        init_t = self.infer(init)
        if init_t != node.type:
            raise TypeError("Expected type {} for {}. Found {}.".format(node_t, name, init_t))

        # Add variable
        self.bind(name, node.type)
        return node

    def check_VarDeclStmt(self, node):
        return VarDeclStmt(self.check(node.decl))

    def check_list(self, seq):
        return [self.check(n) for n in seq]

    def check_Module(self, node):
        return Module(self.check(node.body))
