from lang_ast import *
from cparse import Parser
from lang_types import *

from c_modules import C_VARS, C_TYPES

import os


class Inferer:
    ######### Interface ########

    def __init__(self, *, init_variables=None,
                 init_types=None,
                 extra_includes=None,
                 source_file=None,
                 included_files=None,
                 call_stack=None):
        self.__variables = init_variables or {}
        self.__global_variables = self.__variables
        self.__types = init_types or dict.fromkeys(BUILTIN_TYPES)
        self.__global_types = self.__types
        self.__call_stack = call_stack or []
        self.__found_included_files = included_files or {}
        self.__extra_includes = extra_includes or set()

        # The frame will change each time a new scope is entered
        self.__frames = []

        self.__init_src_file(source_file)

    def __init_src_file(self, source):
        """Set the file source of the ast this inferer will check."""
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

    def bind(self, varname, t):
        """Bind a type to a variable name.

        Args:
            varname (str)
            t (LangType)
        """
        self.assert_type_exists(t)

        if varname in self.__variables:
            assert self.__variables[varname] == t
        else:
            self.__variables[varname] = t

    def lookup(self, varname):
        """Get the type of a variable.

        Args:
            varname (str)

        Returns:
            LangType
        """
        variables = self.__variables
        if varname in variables:
            return variables[varname]
        raise KeyError("Undeclared variable '{}'".format(varname))

    def var_exists(self, varname):
        """Checks if this environment knows of the variable provided."""
        try:
            self.lookup(varname)
        except KeyError:
            return False
        else:
            return True

    def __type_exists(self, t, declared_types):
        assert isinstance(t, LangType)
        if isinstance(t, (ArrayType, PointerType)):
            return self.type_exists(t.contents)
        return t in declared_types

    def type_exists(self, t):
        """Check if a type exists in this scope."""
        return self.__type_exists(t, self.__types)

    def assert_type_exists(self, t):
        if not self.type_exists(t):
            raise RuntimeError("Type '{}' not previously declared.".format(t))

    def assert_type_not_exists(self, t):
        if self.type_exists(t):
            raise RuntimeError("Type '{}' already declared.".format(t))

    def __dump_call_stack(self):
        print("------ Call stack --------")
        for func in self.__call_stack:
            print(func)

    def __call_node_method(self, node, prefix, expected=None):
        """Call a specific method for a node type.

        Args:
            node (ast.Node)
            prefix (str): String describing what to do with the node.
            expected (optional[type]): Expected return type of
                calling "prefix_Node". An error is raised if an expected type
                is passed and the return type is not of that expected type.
        """
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
        """Mark a C standard header that should be included."""
        assert header not in self.__extra_includes
        self.__extra_includes.add(header)

    ####### Type handling ###########

    def types_eq(self, t1, t2):
        """Check if two types are equal."""
        return self.exhaust_typedef_chain(t1) == self.exhaust_typedef_chain(t2)

    def add_type(self, new_type):
        """
        Add a new base type. This is primarily meant for newly declared
        structs.
        """
        self.assert_type_not_exists(new_type)
        self.__types[new_type] = None

    def bind_typedef(self, typename, base_t):
        """Bind a LangType to another LangType to indicate the one type was
        typedef'd to another."""
        self.assert_type_exists(base_t)
        self.assert_type_not_exists(typename)
        self.__types[typename] = base_t

    def exhaust_typedef_chain(self, typedef_t):
        """
        Given a LangType, traverse the known types until we hit a value of None,
        indicating the type used as a key is a base type.
        """
        if isinstance(typedef_t, (PointerType, ArrayType)):
            return typedef_t

        types = self.__types
        actual_t = types[typedef_t]
        while actual_t is not None:
            # Actual is another typedef
            typedef_t = actual_t
            actual_t = types[typedef_t]
        return typedef_t

    def __builtin_type_check(self, t):
        """Check if the type is a builtin one and import the proper module."""
        if t not in self.__types:
            c_header, module = C_TYPES[t.name]
            if c_header not in self.__extra_includes:
                self.add_extra_c_header(c_header)
                self.__check_builtin_module(module)

        self.assert_type_exists(t)
        assert self.__type_exists(t, self.__global_types)

        return t

    ####### Converting TypeMixin nodes to LangTypes ###########

    def langtype_from(self, node):
        assert isinstance(node, TypeMixin)
        return self.__call_node_method(node, "langtype_from", expected=LangType)

    def langtype_from_FuncType(self, node):
        param_nodes = node.params
        return_node = node.returns
        return CallableType(
            [self.langtype_from(p) for p in param_nodes],
            self.langtype_from(return_node)
        )

    def langtype_from_NameType(self, node):
        # Account for typedefs
        t = LangType(node.id)
        if t in self.__types:
            # Exhaust any typedef chains
            return t
        elif node.id in C_TYPES:
            result = self.__builtin_type_check(t)
        else:
            raise RuntimeError("type for name '{}' not previously declared".format(node))
        return result

    def langtype_from_Pointer(self, node):
        return PointerType(self.langtype_from(node.contents))

    def langtype_from_Array(self, node):
        # Infer size b/c it is an expression
        size_t = self.infer(node.size)
        if self.__can_implicit_cast(SIZE_TYPE, size_t):
            return ArrayType(self.langtype_from(node.contents), node.size)
        else:
            raise RuntimeError("Cannot use type '{}' for array size ({}).".format(size_t, node.size))

    def langtype_from_Ellipsis(self, node):
        return VARARG_TYPE

    def langtype_to_typemixin(self, t):
        self.assert_type_exists(t)

        if isinstance(t, PointerType):
            return Pointer(self.langtype_to_typemixin(t.contents))
        elif isinstance(t, ArrayType):
            return Array(self.langtype_to_typemixin(t.contents), t.size)
        elif isinstance(t, CallableType):
            return FuncType(
                [self.langtype_to_typemixin(a) for a in t.args],
                self.langtype_to_typemixin(t.returns)
            )
        elif t == VARARG_TYPE:
            return Ellipsis()
        else:
            return NameType(t.name)

    ######## Type inference ###########

    def infer(self, node):
        """Infer the type of a node."""
        assert isinstance(node, ValueMixin)
        return self.__call_node_method(node, "infer", expected=LangType)

    def infer_Cast(self, node):
        self.infer(node.expr)
        t = self.langtype_from(node.target_type)
        self.assert_type_exists(t)
        return t

    def infer_Call(self, node):
        func = node.func

        # Check for sizeof() since the contents of it do not get evaluated
        if isinstance(func, Name) and func.id == "sizeof":
            # Make sure size_t exists first
            # The arguments of sizeof are not evaluated
            return self.__builtin_type_check(SIZE_TYPE)

        # Evaluate the args
        for arg in node.args:
            self.infer(arg)

        # Check builtin functions
        # Perform if the function is a builtin one and not previously declared
        if isinstance(func, Name) and func.id in C_VARS:
            c_header, module = C_VARS[func.id]
            if c_header not in self.__extra_includes:
                self.add_extra_c_header(c_header)
                self.__check_builtin_module(module)
            assert func.id in self.__variables
            assert func.id in self.__global_variables

        func_t = self.infer(func)
        expanded_t = self.exhaust_typedef_chain(func_t)
        return expanded_t.returns

    def infer_Int(self, node):
        return INT_TYPE

    def infer_Float(self, node):
        return FLOAT_TYPE

    def infer_Name(self, node):
        return self.lookup(node.id)

    def infer_Null(self, node):
        return NULL_TYPE

    def infer_StructPointerDeref(self, node):
        struct_t = self.exhaust_typedef_chain(self.infer(node.value).contents)
        assert isinstance(struct_t, StructType)
        return struct_t.members[node.member]

    def infer_StructMemberAccess(self, node):
        struct_t = self.exhaust_typedef_chain(self.infer(node.value))
        assert isinstance(struct_t, StructType)
        return struct_t.members[node.member]

    def dominant_base_type(self, t1, t2):
        """
        Returns the dominant base type.

        http://stackoverflow.com/a/5563131/2775471
        """
        if t1.name == "void" or t2.name == "void":
            raise RuntimeError("Cannot add to void type")
        elif t1.name == "double" or t2.name == "double":
            return DOUBLE_TYPE
        elif t1.name == "float" or t2.name == "float":
            return FLOAT_TYPE
        elif t1.name == "uint" or t2.name == "uint":
            return UINT_TYPE
        else:
            return INT_TYPE

    def type_is_pointer(self, t):
        return isinstance(self.exhaust_typedef_chain(t), PointerType)

    # TODO: Clean this up and also take into account typedef chains
    def infer_BinOp(self, node):
        left = node.left
        right = node.right
        op = node.op

        left_t = self.infer(left)
        right_t = self.infer(right)

        if op == Add() or op == Sub():
            # Check for shifting pointers
            if self.type_is_pointer(right_t):
                if not self.type_is_integeral(left_t):
                    raise TypeError("Cannot shift pointer in {} with type {}. Expected an integral.".formay(
                        node, left_t
                    ))
                return right_t
            elif self.type_is_pointer(left_t):
                if not self.type_is_integeral(right_t):
                    raise TypeError("Cannot shift pointer in {} with type {}. Expected an integral.".formay(
                        node, right_t
                    ))
                return left_t

        # Otherwise both types must be numeric
        if not self.type_is_numeric(left_t):
            raise typeerror("cannot perform binary operation '{}' on type '{}' in {}".format(
                op, left_t, node
            ))

        if not self.type_is_numeric(right_t):
            raise typeerror("cannot perform binary operation '{}' on type '{}' in {}".format(
                op, right_t, node
            ))

        return self.dominant_base_type(left_t, right_t)

    def infer_BitwiseOp(self, node):
        return self.infer_IntegralOp(node)

    def type_is_integeral(self, t):
        return is_integral_type(self.exhaust_typedef_chain(t))

    def type_is_numeric(self, t):
        return is_numeric_type(self.exhaust_typedef_chain(t))

    def infer_IntegralOp(self, node):
        left_t = self.infer(node.left)
        if not self.type_is_integeral(left_t):
            raise TypeError("Expected LHS of {} to be an integral type. Found {}.".format(
                node, left_t
            ))

        right_t = self.infer(node.right)
        if not self.type_is_integeral(right_t):
            raise TypeError("Expected RHS of {} to be an integral type. Found {}.".format(
                node, right_t
            ))

        return INT_TYPE

    def infer_PostInc(self, node):
        return self.infer(node.value)

    def infer_PostDec(self, node):
        return self.infer(node.value)

    def infer_PreInc(self, node):
        return self.infer(node.value)

    def infer_PreDec(self, node):
        return self.infer(node.value)

    def infer_Char(self, node):
        return CHAR_TYPE

    def infer_ArrayLiteral(self, node):
        content_ts = [self.infer(c) for c in node.contents]

        # Assert all are same contents
        base_t = content_ts[0]
        for content_t in content_ts[1:]:
            assert self.types_eq(content_t, base_t)

        return ArrayType(base_t, Int(len(content_ts)))

    def type_is_container(self, t):
        return is_container_type(self.exhaust_typedef_chain(t))

    def infer_Index(self, node):
        value = node.value

        value_t = self.infer(value)
        if not self.type_is_container(value_t):
            raise TypeError("Could not index {} b/c it is not an array or pointer. Found {}.".format(value, value_t))

        index_t = self.infer(node.index)
        if not self.__can_implicit_cast(SIZE_TYPE, index_t):
            raise TypeError("Cannot index with type '{}'".format(index_t))

        return self.exhaust_typedef_chain(value_t).contents

    def infer_Str(self, node):
        if isinstance(node, Str):
            return ArrayType(CHAR_TYPE, Int(len(node.s) + 1))  # +1 for the null char
        else:
            return PointerType(CHAR_TYPE)

    def infer_AddressOf(self, node):
        return PointerType(self.infer(node.value))

    def infer_LogicalOp(self, node):
        self.infer(node.left)
        self.infer(node.right)
        return INT_TYPE

    def infer_UnaryOp(self, node):
        op = node.op
        node_t = self.infer(node.value)

        if isinstance(op, (UAdd, USub)):
            return node_t

        if isinstance(op, Invert) and not self.type_is_integeral(node_t):
            raise TypeError("Invert operation cannot be performed on '{}' since it is of type '{}' and inversion expects an int type.".format(node.value, node_t))

        return INT_TYPE

    def infer_Deref(self, node):
        value = node.value
        value_t = self.infer(value)
        if not self.type_is_pointer(value_t):
            raise TypeError("Attempting to dereference {} which is of type {} and not a pointer.".format(value, value_t))

        contents_t = self.exhaust_typedef_chain(value_t).contents
        final_contents_t = self.exhaust_typedef_chain(contents_t)
        if final_contents_t == VOID_TYPE:
            raise TypeError("Cannot derefernce a void pointer ({})".format(value))

        return contents_t

    ######## Node checking ###########

    def check(self, node):
        return self.__call_node_method(node, "check", expected=Node)

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
        struct_t.members = {d.name: self.langtype_from(d.type) for d in node.struct.decls}

        for t in struct_t.members.values():
            self.assert_type_exists(t)
        return node

    def check_FuncDecl(self, node):
        func_t = self.langtype_from(node.as_func_type())
        self.assert_type_exists(func_t.returns)
        for param in func_t.args:
            self.assert_type_exists(param)

        # Declaring a function creates the type
        if not self.type_exists(func_t):
            self.add_type(func_t)

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
            assert isinstance(param, (VarDecl, Ellipsis))

    def check_FuncDef(self, node):
        # Check for main function
        if node.name == "main":
            node = self._check_and_create_main(node)

        name = node.name
        node_params = node.params

        # Check the function signiature
        returns = node.returns
        if self.var_exists(name):
            # Func was previously declared
            # Check and match parameters and types
            expected_func_t = self.lookup(name)

            assert isinstance(expected_func_t, CallableType)

            if expected_func_t.args and expected_func_t.args[-1].name == "vararg":
                # Check to make sure there is only one varargtype at the end
                # of the arguments list
                if len(expected_func_t.args) == 1:
                    raise RuntimeError("Expected 1 argument before Ellipsis")

                # Check for only 1 vararg
                for i in range(len(expected_func_t.args)-1, -1, -1):
                    if expected_func_t.args[i].name == "vararg":
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
                        VarDecl(param, self.langtype_to_typemixin(expected_param_t))
                    )
                elif param.type != expected_func_t.params[i]:
                    raise RuntimeError("Expected {} to be of type {} from previous declaration".format(param.name))
                else:
                    new_node_params.append(param)
            node_params = new_node_params

            # Check and replace returns
            expected_returns = expected_func_t.returns
            if node.returns:
                returns_t = self.langtype_from(node.returns)
                assert returns_t == expected_returns, "Expected {}. Found {}.".format(expected_returns, returns_t)
            returns = self.langtype_to_typemixin(expected_returns)
        else:
            # First instance of function
            # TODO: Will need to perform type inference when calling function
            # For now, just make sure the function has variable declarations
            # as its arguments and a return type.
            self._assert_args_as_vardecls(node.params)
            assert isinstance(returns, TypeMixin)

            # Create this type
            func_t = self.langtype_from(FuncType(
                [p if isinstance(p, Ellipsis) else p.type for p in node.params],
                returns
            ))

            if not self.type_exists(func_t):
                self.add_type(func_t)

            # Bind this variable
            self.bind(name, func_t)

        # Add the params to the scope
        self.enter_scope()
        for param in node_params:
            param_t = self.langtype_from(param.type)
            self.bind(param.name, param_t)
        body = [self.check(n) for n in node.body]
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
            if self.var_exists(name):
                expected_t = self.lookup(name)
                if expected_t != right_t:
                    raise TypeError("Expected type {} for {}. Found {}.".format(expected_t, name, right_t))
                return node
            else:
                # The default type for the vardecl will be the type of the RHS
                # Apply any necessary changes
                assign_t = right_t

                if (isinstance(right_t, ArrayType) and
                        not isinstance(right, ArrayLiteral) and
                        not isinstance(right, Str)):
                    # RHS is array type, but not an array literal -> assign as
                    # pointer
                    assign_t = PointerType(right_t.contents)

                # First instance of this variable
                # Change to a VarDecl
                return self.check(VarDeclStmt(VarDecl(
                    name,
                    self.langtype_to_typemixin(assign_t),
                    right
                )))
        elif isinstance(left, StructPointerDeref):
            # Get the struct and check the member
            value = left.value
            member = left.member

            value_t = self.infer(value)
            value_contents_t = self.exhaust_typedef_chain(value_t.contents)
            expected_t = value_contents_t.members[member]

            # See if can assign
            self.__check_assignable(expected_t, right_t, right,
                                    "member {} of struct {}".format(member, value_t.contents.name))

            return node
        elif isinstance(left, StructMemberAccess):
            # Get the struct and check the member
            value = left.value
            member = left.member

            value_t = self.infer(value)
            value_t = self.exhaust_typedef_chain(value_t)
            expected_t = value_t.members[member]

            # See if can assign
            self.__check_assignable(expected_t, right_t, right,
                                    "member {} of struct {}".format(member, value_t.name))

            return node
        elif isinstance(left, Index):
            # Get the array and check the contents
            value = left.value
            index = left.index

            value_t = self.infer(value)
            expected_t = self.exhaust_typedef_chain(value_t.contents)

            # See if can assign
            self.__check_assignable(
                expected_t, right_t, right,
                "contents of pointer/array {}".format(value)
            )
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
        base_t = self.langtype_from(node.type)
        self.assert_type_exists(base_t)
        self.bind_typedef(LangType(node.name), base_t)
        return node

    def check_ExprStmt(self, node):
        if isinstance(node.value, Str):
            return Pass()
        self.infer(node.value)
        return node

    def __check_assignable(self, expected_t, value_t, value_node, varname):
        expected_t = self.exhaust_typedef_chain(expected_t)
        value_t = self.exhaust_typedef_chain(value_t)

        # Array literals to arrays of anything
        if isinstance(value_node, ArrayLiteral):
            return isinstance(expected_t, ArrayType)

        if isinstance(value_t, ArrayType):
            return isinstance(expected_t, PointerType)

        # Null to pointer
        if isinstance(expected_t, PointerType) and value_t == NULL_TYPE:
            return True

        # Void pointer to any pointer
        if isinstance(expected_t, PointerType) and value_t == PointerType(VOID_TYPE):
            return True

        if expected_t != value_t and not self.__can_implicit_cast(expected_t, value_t):
            raise TypeError("Expected type {} for {}. Could not implicitely assign {} to {}.".format(expected_t, varname, value_t, expected_t))

    def __can_implicit_cast(self, target_t, value_t):
        """Check if the value type can be implicitely converted to the target
        type."""
        # For when sizeof is called but the size_t type has not been
        # explicitely typedef'd
        # TODO: Make size_t a builtin type to avoid having to do this check
        if target_t == SIZE_TYPE or value_t == SIZE_TYPE:
            self.__builtin_type_check(SIZE_TYPE)
        return can_implicit_assign(
            self.exhaust_typedef_chain(target_t),
            self.exhaust_typedef_chain(value_t),
        )

    def check_VarDecl(self, node):
        node_t = self.langtype_from(node.type)

        self.assert_type_exists(node_t)
        name = node.name
        init = node.init

        # Make sure the variable is not declared in the same scope
        if self.var_exists(name):
            raise RuntimeError("Cannot declare variable '{}' again in same scope".format(name))

        # Check types
        if init:
            init_t = self.infer(init)
            self.__check_assignable(node_t, init_t, init, name)

        # Add variable
        self.bind(name, node_t)
        return node

    def check_VarDeclStmt(self, node):
        return VarDeclStmt(self.check(node.decl))

    def check_While(self, node):
        self.infer(node.test)
        return While(
            node.test,
            [self.check(n) for n in node.body],
            [self.check(n) for n in node.orelse],
        )

    def check_DoWhile(self, node):
        self.infer(node.test)
        return DoWhile(
            node.test,
            [self.check(n) for n in node.body]
        )

    def check_If(self, node):
        self.infer(node.test)
        return If(
            node.test,
            [self.check(n) for n in node.body],
            [self.check(n) for n in node.orelse]
        )

    def check_EnumDecl(self, node):
        # Create an enum type
        enum_t = LangType(node.enum.name)
        self.add_type(enum_t)

        for member in node.enum.members:
            self.bind(member, enum_t)

        return node

    def check_Switch(self, node):
        self.infer(node.test)
        return Switch(
            node.test,
            [self.check(n) for n in node.cases]
        )

    def check_Case(self, node):
        for test in node.tests:
            self.infer(test)
        return Case(
            node.tests,
            [self.check(n) for n in node.body]
        )

    def check_Break(self, node):
        return node

    def check_Pass(self, node):
        return node

    def check_Default(self, node):
        return Default(
            [self.check(n) for n in node.body]
        )

    def __check_module(self, node, *, is_base_module=False):
        if is_base_module and node.filename:
            self.__init_src_file(node.filename)

        checked_body = [self.check(n) for n in node.body]

        # Add extra includes
        if is_base_module:
            extra_includes = list(map(CInclude, self.__extra_includes))
            checked_body = extra_includes + checked_body

        return Module(checked_body, node.filename)

    def __check_builtin_module(self, node):
        # Make the global scope the current one
        saved_vars = self.__variables
        saved_types = self.__types
        self.__variables = self.__global_variables
        self.__types = self.__global_types

        # Check normally
        self.__check_module(node)

        # Switch back to the local one
        self.__variables = saved_vars
        self.__types = saved_types

        # Merge new variables from global into local
        self.__variables.update(self.__global_variables)
        self.__types.update(self.__global_types)

    def check_Module(self, node):
        return self.__check_module(node, is_base_module=True)


# Check langtype_from functions were implemented for all type mixins
for name, mixin in TYPE_MIXINS:
    assert hasattr(Inferer, "langtype_from_" + name)
