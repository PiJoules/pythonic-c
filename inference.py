from lang_ast import *
from cparse import Parser
from lang_types import *

from c_modules import C_VARS, C_TYPES

import os


class Frame:
    """Class containing the scope of types at runtime that change when enetring
    new frames like in new functions."""

    def __init__(self, variables, types, classes, parent=None):
        """
        Args:
            variables (dict[str, LangType])
            parent (optional[Frame])
            types (dict[LangType, (LangType, NoneType))
            classes (dict[LangType, ClassType])
        """
        self.__parent = parent
        self.__variables = variables
        self.__types = types
        self.__classes = classes

    def classes(self):
        return self.__classes

    # Variables interface

    def variables(self):
        return self.__variables

    def lookup(self, varname):
        """Lookup in parent frames."""
        if varname in self.__variables:
            return self.__variables[varname]

        if self.__parent is not None:
            return self.__parent.lookup(varname)

        raise KeyError("Unknown variable '{}'".format(varname))

    def var_exists(self, varname):
        try:
            self.lookup(varname)
        except KeyError:
            return False
        else:
            return True

    # Types interface

    def types(self):
        return self.__types

    def exhaust_typedef(self, t):
        if isinstance(typedef_t, (PointerType, ArrayType)):
            return typedef_t

        types = self.__types
        actual_t = types[typedef_t]
        while actual_t is not None:
            # Actual is another typedef
            typedef_t = actual_t
            actual_t = types[typedef_t]
        return typedef_t

    def parent(self):
        return self.__parent

    def is_global(self):
        return self.__parent is None

    def enter_scope(self):
        return Frame(
            dict(self.__variables),
            dict(self.__types),
            dict(self.__classes),
            parent=self
        )

    def switch_global(self):
        """Return the global scope on a stack."""
        frame = self
        while not frame.is_global():
            frame = frame.parent()
        return Frame(
            frame.variables(),
            frame.types(),
            frame.classes(),
            parent=self,
        )

    def exit_scope(self):
        parent = self.__parent
        if not parent:
            raise RuntimeError("Global frame has no parent.")
        return parent


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
        self.__classes = {}
        self.__global_classes = self.__classes
        self.__global_types = self.__types
        self.__call_stack = call_stack or []
        self.__found_included_files = included_files or {}
        self.__extra_includes = extra_includes or set()
        self.__bounded_methods = set()

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
            self.__classes,
        ))

        self.__variables = dict(self.__variables)
        self.__types = dict(self.__types)
        self.__classes = dict(self.__classes)

    def exit_scope(self):
        """
        Called to reset the attributes that should bot be edited of the
        previous scope y popping them from the frame.
        """
        frame_attrs = self.__frames.pop()
        self.__variables = frame_attrs[0]
        self.__types = frame_attrs[1]
        self.__classes = frame_attrs[2]

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
        return self.exhaust_typedef(t1) == self.exhaust_typedef(t2)

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

    def exhaust_typedef(self, typedef_t):
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
        return CallableType(
            [self.langtype_from(p) for p in node.params],
            self.langtype_from(node.returns),
            is_bound=node.is_bound,
            inst=node.inst,
        )

    def langtype_from_NameType(self, node):
        # Account for typedefs
        t = LangType(node.id)
        if self.type_exists(t):
            # Exhaust any typedef chains
            return t
        elif node.id in C_TYPES:
            return self.__builtin_type_check(t)
        elif node.id in self.__classes:
            return self.__classes[node.id]
        else:
            raise RuntimeError("type for name '{}' not previously declared".format(node.id))

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

    def langtype_from_Generic(self, node):
        raise NotImplementedError

    def langtype_to_typemixin(self, t):
        self.assert_type_exists(t)

        if isinstance(t, PointerType):
            return Pointer(self.langtype_to_typemixin(t.contents))
        elif isinstance(t, ArrayType):
            return Array(self.langtype_to_typemixin(t.contents), t.size)
        elif isinstance(t, CallableType):
            return FuncType(
                [self.langtype_to_typemixin(a) for a in t.args],
                self.langtype_to_typemixin(t.returns),
                is_bound=t.is_bound,
                inst=t.inst,
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
        return self.langtype_from(node.target_type)

    def infer_Call(self, node):
        func = node.func

        # Check for sizeof() since the contents of it do not get evaluated
        if isinstance(func, Name) and func.id == "sizeof":
            # Make sure size_t exists first
            # The arguments of sizeof are not evaluated
            return self.__builtin_type_check(SIZE_TYPE)

        func_t = self.infer(func)
        expanded_t = self.exhaust_typedef(func_t)
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
        struct_t = self.exhaust_typedef(
            self.exhaust_typedef(self.infer(node.value)).contents)
        assert isinstance(struct_t, StructType)
        member_t = struct_t.members[node.member]

        if struct_t.name in self.__classes:
            if isinstance(member_t, CallableType):
                return CallableType(
                    member_t.args,
                    member_t.returns,
                    is_bound=True,
                    inst=node.value,
                )

        return member_t

    def infer_StructMemberAccess(self, node):
        struct_t = self.exhaust_typedef(self.infer(node.value))
        assert isinstance(struct_t, StructType)
        member_t = struct_t.members[node.member]

        if struct_t.name in self.__classes:
            if isinstance(member_t, CallableType):
                # Value is the struct and not a pointer, so will need to
                # adderess-of it.
                return CallableType(
                    member_t.args,
                    member_t.returns,
                    is_bound=True,
                    inst=AddressOf(node.value),
                )

        return member_t

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
        return isinstance(self.exhaust_typedef(t), PointerType)

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
            raise TypeError("cannot perform binary operation '{}' on type '{}' in {}".format(
                op, left_t, node
            ))

        if not self.type_is_numeric(right_t):
            raise TypeError("cannot perform binary operation '{}' on type '{}' in {}".format(
                op, right_t, node
            ))

        return self.dominant_base_type(left_t, right_t)

    def infer_BitwiseOp(self, node):
        return self.infer_IntegralOp(node)

    def type_is_integeral(self, t):
        return is_integral_type(self.exhaust_typedef(t))

    def type_is_numeric(self, t):
        return is_numeric_type(self.exhaust_typedef(t))

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
        return is_container_type(self.exhaust_typedef(t))

    def infer_Index(self, node):
        value = node.value

        value_t = self.infer(value)
        if not self.type_is_container(value_t):
            raise TypeError("Could not index {} b/c it is not an array or pointer. Found {}.".format(value, value_t))

        index_t = self.infer(node.index)
        if not self.__can_implicit_cast(SIZE_TYPE, index_t):
            raise TypeError("Cannot index with type '{}'".format(index_t))

        return self.exhaust_typedef(value_t).contents

    def infer_Str(self, node):
        if isinstance(node, Str):
            return ArrayType(CHAR_TYPE, Int(len(node.s) + 1))  # +1 for the null char
        else:
            return PointerType(CHAR_TYPE)

    def infer_AddressOf(self, node):
        return PointerType(self.infer(node.value))

    def infer_LogicalOp(self, node):
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

        contents_t = self.exhaust_typedef(value_t).contents
        if self.types_eq(contents_t, VOID_TYPE):
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
            if isinstance(t, CallableType) and not self.type_exists(t):
                self.add_type(t)
            self.assert_type_exists(t)
        return node

    def check_Ellipsis(self, node):
        return node

    def check_FuncDecl(self, node):
        node = FuncDecl(
            node.name,
            node.params,  # DO NOT NEED TO CHECK THE FUNCTION ARGUMENTS
            self.check(node.returns),
        )

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
                assert returns_t == expected_returns, "Expected {}. Found {}. ({})".format(expected_returns, returns_t, node.loc())
            returns = self.langtype_to_typemixin(expected_returns)
        else:
            # First instance of function
            # TODO: Will need to perform type inference when calling function
            # For now, just make sure the function has variable declarations
            # as its arguments and a return type.
            self._assert_args_as_vardecls(node.params)

            if not returns:
                returns = NameType("int")
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

    def checkassign_Name(self, node):
        right = node.right
        right_t = self.infer(right)

        name = node.left.id
        if self.var_exists(name):
            expected_t = self.lookup(name)
            if not self.types_eq(expected_t, right_t):
                raise TypeError("Expected type {} for {}. Found {} at {}.".format(expected_t, name, right_t, right.loc()))

            expected_t = self.exhaust_typedef(expected_t)
            right_t = self.exhaust_typedef(right_t)

            if isinstance(expected_t, CallableType):
                expected_t.is_bound = right_t.is_bound
                expected_t.inst = right_t.inst

            return node
        else:
            # First instance of this variable. Change to a VarDecl.
            # The default type for the vardecl will be the type of the RHS
            # Apply any necessary changes
            assign_t = right_t

            if (isinstance(right_t, ArrayType) and
                    not isinstance(right, ArrayLiteral) and
                    not isinstance(right, Str)):
                # RHS is array type, but not an array literal -> assign as
                # pointer
                assign_t = PointerType(right_t.contents)

            assign_node_t = self.langtype_to_typemixin(assign_t)

            return self.check(VarDeclStmt(VarDecl(
                name,
                assign_node_t,
                right
            )))

    def checkassign_Deref(self, node):
        left = node.left
        right = node.right
        right_t = self.infer(right)

        # Get the pointer value
        left_t = self.infer(left)
        expected_t = self.exhaust_typedef(left_t)
        self.__check_assignable(
            expected_t, right_t, right,
            "Contents of {}".format(left_t)
        )

        # Pass callable inst
        right_t = self.exhaust_typedef(right_t)
        if isinstance(expected_t, CallableType):
            self.copy_inst(expected_t, right_t)

        return node

    def checkassign_StructPointerDeref(self, node):
        left = node.left
        right = node.right
        right_t = self.infer(right)

        # Get the struct and check the member
        value = left.value
        member = left.member

        value_t = self.infer(value)
        final_value_t = self.exhaust_typedef(value_t)  # Struct pointer
        contents_t = final_value_t.contents
        struct_t = self.exhaust_typedef(contents_t)  # Struct
        expected_t = struct_t.members[member]

        # See if can assign
        self.__check_assignable(
            expected_t, right_t, right,
            "member {} of struct {}".format(member, struct_t.name)
        )

        # Pass callable inst
        right_t = self.exhaust_typedef(right_t)
        expected_t = self.exhaust_typedef(expected_t)
        if isinstance(expected_t, CallableType):
            self.copy_inst(expected_t, right_t)

        return node

    def checkassign_StructMemberAccess(self, node):
        left = node.left
        right = node.right
        right_t = self.infer(right)

        # Get the struct and check the member
        value = left.value
        member = left.member

        value_t = self.infer(value)
        struct_t = self.exhaust_typedef(value_t)  # Struct
        expected_t = struct_t.members[member]

        # See if can assign
        self.__check_assignable(
            expected_t, right_t, right,
            "member {} of struct {}".format(member, struct_t.name)
        )

        # Pass callable inst
        right_t = self.exhaust_typedef(right_t)
        expected_t = self.exhaust_typedef(expected_t)
        if isinstance(expected_t, CallableType):
            self.copy_inst(expected_t, right_t)

        return node

    def copy_inst(self, c1, c2):
        c1.is_bound = c2.is_bound
        c1.inst = c2.inst

    def checkassign_Index(self, node):
        left = node.left
        right = node.right
        right_t = self.infer(right)

        # Get the array and check the contents
        value = left.value

        value_t = self.infer(value)
        container_t = self.exhaust_typedef(value_t)  # Pointer/Array
        expected_t = self.exhaust_typedef(container_t.contents)

        # See if can assign
        self.__check_assignable(
            expected_t, right_t, right,
            "contents of pointer/array {}".format(value)
        )

        # Pass callable inst
        right_t = self.exhaust_typedef(right_t)
        if isinstance(expected_t, CallableType):
            self.copy_inst(expected_t, right_t)

        return node

    def check_Assign(self, node):
        node = Assign(
            self.check(node.left),
            self.check(node.right)
        )

        left_node_name = type(node.left).__name__
        return getattr(self, "checkassign_" + left_node_name)(node)

    def check_Return(self, node):
        return Return(self.check(node.value))

    def check_Ifndef(self, node):
        return node

    def check_Endif(self, node):
        return node

    def check_TypeDefStmt(self, node):
        node = TypeDefStmt(
            self.check(node.type),
            node.name
        )

        base_t = self.langtype_from(node.type)
        self.assert_type_exists(base_t)
        self.bind_typedef(LangType(node.name), base_t)
        return node

    def check_BinOp(self, node):
        return BinOp(
            self.check(node.left),
            node.op,
            self.check(node.right),
        )

    def check_UnaryOp(self, node):
        return UnaryOp(
            node.op,
            self.check(node.value)
        )

    def check_ArrayLiteral(self, node):
        return ArrayLiteral([self.check(n) for n in node.contents])

    def check_Name(self, node):
        if node.id in C_VARS:
            c_header, module = C_VARS[node.id]
            if c_header not in self.__extra_includes:
                self.add_extra_c_header(c_header)
                self.__check_builtin_module(module)
            assert node.id in self.__variables
            assert node.id in self.__global_variables
        return node

    def check_StructPointerDeref(self, node):
        return node

    def check_Call(self, node):
        node = Call(
            self.check(node.func),
            [self.check(a) for a in node.args]
        )

        func = node.func
        args = node.args

        if isinstance(func, Name) and func.id == "sizeof":
            # The contents of sizeof do not get evaluated
            return node

        func_t = self.exhaust_typedef(self.infer(func))
        if func_t.is_bound:
            args.insert(0, func_t.inst)

        return node

    # TODO: Check for class types in these later
    def check_Index(self, node):
        return Index(
            self.check(node.value),
            self.check(node.index)
        )

    def check_PostInc(self, node):
        return PostInc(self.check(node.value))

    def check_PostDec(self, node):
        return PostDec(self.check(node.value))

    def check_PreInc(self, node):
        return PreInc(self.check(node.value))

    def check_PreDec(self, node):
        return PreDec(self.check(node.value))

    def check_LogicalOp(self, node):
        return LogicalOp(
            self.check(node.left),
            node.op,
            self.check(node.right),
        )

    def check_IntegralOp(self, node):
        return IntegralOp(
            self.check(node.left),
            node.op,
            self.check(node.right),
        )

    def check_BitwiseOp(self, node):
        return BitwiseOp(
            self.check(node.left),
            node.op,
            self.check(node.right),
        )

    def check_Null(self, node):
        return node

    def check_ExprStmt(self, node):
        if isinstance(node.value, Str):
            # String comment
            return Pass()
        return ExprStmt(self.check(node.value))

    def __check_assignable(self, expected_t, value_t, value_node, varname):
        expected_t = self.exhaust_typedef(expected_t)
        value_t = self.exhaust_typedef(value_t)

        # Array literals to arrays of anything
        if isinstance(value_node, ArrayLiteral) and isinstance(expected_t, ArrayType):
            return

        if isinstance(value_t, ArrayType) and isinstance(expected_t, PointerType):
            return

        # Null to pointer
        if isinstance(expected_t, PointerType) and value_t == NULL_TYPE:
            return

        # Void pointer to any pointer
        if isinstance(expected_t, PointerType) and value_t == PointerType(VOID_TYPE):
            return

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
            self.exhaust_typedef(target_t),
            self.exhaust_typedef(value_t),
        )

    def check_NameType(self, node):
        return node

    def check_Array(self, node):
        return Array(
            self.check(node.contents),
            self.check(node.size)
        )

    def check_Str(self, node):
        return node

    def check_Pointer(self, node):
        return Pointer(self.check(node.contents))

    def check_Cast(self, node):
        return Cast(
            self.check(node.target_type),
            self.check(node.expr)
        )

    def check_FuncType(self, node):
        return FuncType(
            [self.check(p) for p in node.params],
            self.check(node.returns),
            is_bound=node.is_bound,
            inst=self.check(node.inst) if node.inst else node.inst
        )

    def check_AddressOf(self, node):
        return AddressOf(self.check(node.value))

    def check_Deref(self, node):
        return Deref(self.check(node.value))

    def check_StructMemberAccess(self, node):
        return StructMemberAccess(
            self.check(node.value),
            node.member
        )

    def check_Char(self, node):
        return node

    def check_Float(self, node):
        return node

    def check_VarDecl(self, node):
        node = VarDecl(
            node.name,
            self.check(node.type),
            self.check(node.init) if node.init else node.init
        )

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

            node_t = self.exhaust_typedef(node_t)
            init_t = self.exhaust_typedef(init_t)

            # Pass any bounded instances
            if isinstance(node_t, CallableType):
                node_t.is_bound = init_t.is_bound
                node_t.inst = init_t.inst

        # Add variable
        self.bind(name, node_t)
        return node

    def check_VarDeclStmt(self, node):
        return VarDeclStmt(self.check(node.decl))

    def check_While(self, node):
        return While(
            self.check(node.test),
            [self.check(n) for n in node.body],
            [self.check(n) for n in node.orelse],
        )

    def check_DoWhile(self, node):
        return DoWhile(
            self.check(node.test),
            [self.check(n) for n in node.body]
        )

    def check_If(self, node):
        return If(
            self.check(node.test),
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
        return Switch(
            self.check(node.test),
            [self.check(n) for n in node.cases]
        )

    def check_Case(self, node):
        return Case(
            [self.check(t) for t in node.tests],
            [self.check(n) for n in node.body]
        )

    def check_Int(self, node):
        return node

    def check_Break(self, node):
        return node

    def check_Pass(self, node):
        return node

    def check_Default(self, node):
        return Default(
            [self.check(n) for n in node.body]
        )

    def check_ClassDef(self, node):
        name = node.name
        func_typename = node.name
        self.__classes[name] = None

        generics = node.generics
        if generics:
            raise NotImplementedError("No logic yet implemented for generic types.")

        parents = node.parents
        if parents:
            raise NotImplementedError("No logic yet implemented for subclassing.")

        # Initialize the properties of the class type
        body = node.body
        attrs = {}
        funcdecls = {}
        funcdefs = {}
        for n in body:
            if isinstance(n, VarDeclStmt):
                attrs[n.decl.name] = n.decl
            elif isinstance(n, Assign):
                if not isinstance(n.left, Name):
                    raise RuntimeError("Expected a name for assigning to class attribute at {}".format(
                        n.left.loc(),
                    ))
                attrs[n.left.id] = VarDecl(
                    n.left.id,
                    self.langtype_to_typemixin(self.infer(n.right)),
                    n.right
                )
            elif isinstance(n, FuncDecl):
                funcdecls[n.name] = n
            elif isinstance(n, FuncDef):
                if n.name in funcdecls:
                    # Check that the signatures are equal
                    raise NotImplementedError
                else:
                    # Assert all params are VarDecls, return type is specified,
                    # and add the func to the class
                    self._assert_args_as_vardecls(n.params)

                    if not n.returns:
                        n.returns = NameType("int")
                    assert isinstance(n.returns, TypeMixin)

                    funcdecls[n.name] = n.as_func_decl()
                    funcdefs[n.name] = n
            elif isinstance(n, Pass):
                pass
            else:
                raise RuntimeError("Expected only {} in ClassDef ({})".format(
                    ALLOWED_CLASS_NODES, node.loc()
                ))

        assert set(funcdecls.keys()) == set(funcdefs.keys())

        # Create the class struct
        struct_decl = self.check(StructDecl(Struct(
            func_typename,

            # Remove any inits
            [VarDecl(p.name, p.type) for p in attrs.values()] +
            [VarDecl(f.name, f.as_func_type()) for f in funcdecls.values()]
        )))

        # Create the methods
        methods = []
        for name, funcdef in funcdefs.items():
            funcdef.name = node.name + "_" + name
            methods.append(self.check(funcdef))

        # Create the constructor function
        if "__init__" in funcdecls:
            init_params = funcdecls["__init__"].params[1:]
        else:
            init_params = []
        init_args = [Name(p.name) for p in init_params]

        cls_ptr_type = Pointer(NameType(func_typename))
        constr_func_body = [
            # Create the object
            VarDeclStmt(VarDecl(
                "obj",
                cls_ptr_type,
                Cast(
                    cls_ptr_type,
                    Call(
                        Name("malloc"),
                        [Call(Name("sizeof"), [Name(func_typename)])]
                    )
                )
            ))
        ]

        # Set any default values
        for name, vardecl in attrs.items():
            init = vardecl.init
            if init:
                constr_func_body.append(Assign(
                    StructPointerDeref(Name("obj"), name),
                    init
                ))

        for name, funcdecl in funcdecls.items():
            constr_func_body.append(Assign(
                StructPointerDeref(Name("obj"), name),
                Name(node.name + "_" + name)
            ))

        if "__init__" in funcdecls:
            constr_func_body += [
                # Initialize
                ExprStmt(Call(Name(node.name + "___init__"),
                              [Name("obj")] + init_args)),
                ]

        constr_func_body += [
            # Return it
            Return(Name("obj")),
        ]

        constr_func = self.check(FuncDef(
            "new_" + node.name,
            init_params,
            constr_func_body,
            cls_ptr_type
        ))

        # Create destructor function
        if "__del__" in funcdecls:
            # Call __del__
            del_func = funcdecls["__del__"]
            dtor_func_body = [ExprStmt(Call(
                Name(node.name + "___del__"),
                [Name("self")]
            ))]
        else:
            dtor_func_body = []
        dtor_func_body += [
            ExprStmt(Call(Name("free"), [Name("self")]))
        ]

        dtor_func = self.check(FuncDef(
            "del_" + node.name,
            [VarDecl("self", cls_ptr_type)],
            dtor_func_body,
            NameType("void"),
        ))

        # Finalize the group
        body = [struct_decl] + methods + [constr_func, dtor_func]
        group = StmtGroup(body)

        # If the source file for this inferer was provided, dump the C code of
        # this class in a header and source file. Otherwise, return the node
        # and dump the C code in the original file.
        if self.__source:
            pass

        return group

    def check_StmtGroup(self, node):
        return StmtGroup([self.check(n) for n in node.body])

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
        saved_classes = self.__classes
        self.__variables = self.__global_variables
        self.__types = self.__global_types
        self.__classes = self.__global_classes

        # Check normally
        self.__check_module(node)

        # Switch back to the local one
        self.__variables = saved_vars
        self.__types = saved_types
        self.__classes = saved_classes

        # Merge new variables from global into local
        # TODO: This only accounts for 1 layer down. Need to update for more
        # nested functions.
        self.__variables.update(self.__global_variables)
        self.__types.update(self.__global_types)
        self.__classes.update(self.__global_classes)

    def check_Module(self, node):
        return self.__check_module(node, is_base_module=True)


# Check langtype_from functions were implemented for all type mixins
for name, mixin in TYPE_MIXINS:
    assert hasattr(Inferer, "langtype_from_" + name)

# Same for the assignable types
for name, mixin in ASSIGNABLE_MIXINS:
    assert hasattr(Inferer, "checkassign_" + name)
