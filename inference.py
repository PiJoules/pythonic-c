from lang_ast import *
from cparse import Parser
from clibs import INIT_LIBS

import os


INIT_TYPES = {
    "int", "uint",
    "float", "void", "char"
}


class Inferer:
    ######### Interface ########

    def __init__(self, init_variables=None, init_types=INIT_TYPES,
                 source_dir=None, parent=None,
                 init_libs=INIT_LIBS):
        self.__variables = init_variables or {}
        self.__types = init_types or set()
        self.__source_dir = source_dir or os.getcwd()
        self.__parent = parent
        self.__libs = init_libs or {}

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

    def assert_type_exists(self, type):
        if isinstance(type, (Array, Pointer)):
            self.assert_type_exists(type.contents)
        elif not type in self.types():
            raise RuntimeError("Type '{}' not previously declared.".format(type))

    def add_type(self, type):
        self.__types.add(type)

    def __call_node_method(self, node, prefix, expected=None):
        name = node.__class__.__name__
        method_name = prefix + "_" + name
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            result = method(node)
            if expected is not None and not isinstance(result, expected):
                raise RuntimeError("Expected {} back from {}(). Got {}.".format(expected, method_name, type(result)))
            return result
        else:
            raise RuntimeError("No {} method implemented for node '{}'. Implement {}(self, node) to check this type of node".format(
                prefix,
                name,
                method_name
            ))

    ######## Type inference ###########

    def infer(self, node):
        return self.__call_node_method(node, "infer", expected=LANG_TYPES)

    def infer_Cast(self, node):
        return node.target_type

    ######## Node checking ###########

    def check(self, node):
        return self.__call_node_method(node, "check", expected=Node)

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
        self.add_type(node.struct.name)
        for member, type in node.struct.members().items():
            self.assert_type_exists(type)
        return node

    def check_FuncDecl(self, node):
        func_t = node.type()
        self.assert_type_exists(func_t.returns)
        for param in func_t.params:
            self.assert_type_exists(param)
        self.add_type(func_t)
        self.bind(node.name, func_t)
        return node

    def check_IncludeLocal(self, node):
        parser = Parser()
        path = os.path.join(self.__source_dir, node.path.s)
        with open(path, "r") as f:
            module_ast = parser.parse(f.read())
            self.check_module(module_ast)
        return node

    def check_Include(self, node):
        path = node.path.s

        if path not in self.__libs:
            raise RuntimeError("File '{}' not found".format(path))
        else:
            self.check_module(self.__libs[path])

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
        body = self.check_list(node.body)
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
                return VarDeclStmt(VarDecl(
                    name,
                    right_t,
                    right
                ))
        else:
            raise NotImplementedError("Unable to assign to {}".format(left))

    def check_Return(self, node):
        return node

    def check_Ifndef(self, node):
        return node

    def check_Endif(self, node):
        return node

    def check_TypeDefStmt(self, node):
        self.add_type(node.name)
        return node

    def check_list(self, seq):
        return [self.check(n) for n in seq]

    def check_module(self, node):
        return Module(self.check_list(node.body))
