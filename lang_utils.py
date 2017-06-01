import copy


def optional(t):
    if isinstance(t, tuple):
        return t + (type(None), )
    return (t, type(None))


def merge_dicts(d1, d2):
    d = {}
    d.update(d1)
    d.update(d2)
    return d


# Used to prevent infinite recurson when calling __eq__ on SlottedClasses with
# circular references
CHECKED_IDS = set()


class SlottedClassChecker(type):
    def __new__(cls, name, bases, namespace):
        # Get the attributes
        cls_attrs = namespace.get("__attrs__", tuple())
        cls_types = namespace.get("__types__", {})
        cls_defaults = namespace.get("__defaults__", {})
        cls_extra_attrs = namespace.get("__extra_attrs__", set())

        # Check types
        assert isinstance(cls_attrs, tuple)
        assert isinstance(cls_types, dict)
        assert isinstance(cls_defaults, dict)
        assert isinstance(cls_extra_attrs, set)

        # Combine the slotted class attrs of parent classes
        found_slots = False
        for base in bases:
            assert issubclass(base, SlottedClass), "{} inherits from class {} which must inherit from SlottedClass".format(name, base.__name__)
            base_slots = getattr(base, "__slots__", None)
            if base_slots:
                if not found_slots:
                    found_slots = True
                else:
                    raise RuntimeError("{} found to contain __slots__. Only one class that {} inherits from can contain __slots__ or be a SlotttedCLass".format(base.__name__, name))

            attrs = getattr(base, "__attrs__", tuple())
            cls_attrs = attrs + cls_attrs

            types = getattr(base, "__types__", {})
            cls_types.update(types)

            defaults = getattr(base, "__defaults__", {})
            cls_defaults.update(defaults)

            extra_attrs = getattr(base, "__extra_attrs__", frozenset())
            cls_extra_attrs |= extra_attrs

        # Create and set the slots
        namespace["__attrs__"] = cls_attrs
        namespace["__types__"] = cls_types
        namespace["__defaults__"] = cls_defaults
        namespace["__extra_attrs__"] = cls_extra_attrs

        slots = cls_attrs + tuple(cls_extra_attrs)
        namespace["__slots__"] = slots

        # Check slotted attributes
        attrs = set(slots)
        for attr in cls_types:
            assert attr in attrs, "type '{}' not in __attrs__ for {}".format(attr, cls)
        for attr in cls_defaults:
            assert attr in attrs, "default '{}' not in __attrs__ for {}".format(attr, cls)

        return type.__new__(cls, name, bases, namespace)


class SlottedClass(metaclass=SlottedClassChecker):
    # Ordered attributes
    __attrs__ = tuple()

    # Expected types
    __types__ = {}

    # Default values for types
    __defaults__ = {}

    # Unordered attributes
    __extra_attrs__ = set()

    def __init__(self, *args, **kwargs):
        for i, val in enumerate(args):
            self.assign_and_check(self.__slots__[i], val)

        for attr in self.__slots__[len(args):]:
            if attr not in kwargs:
                val = copy.copy(self.__defaults__[attr])
            else:
                val = kwargs[attr]
            self.assign_and_check(attr, val)

    def assign_and_check(self, attr, val):
        def __raise_type_error(attr, owner_t, expected_t, found_t):
            raise TypeError("Expected '{}' of {} to be type {}. Found {}.".format(
                attr, owner_t, expected_t, found_t
            ))

        def __recursive_check(val, expected, original):
            """Recursively check container items."""
            if isinstance(expected, list):
                if not isinstance(val, list):
                    __raise_type_error(attr, type(self), original, type(val))

                for item in val:
                    __recursive_check(item, expected[0], original)
            elif isinstance(expected, dict):
                if not isinstance(val, dict):
                    __raise_type_error(attr, type(self), original, type(val))

                for k in val.keys():
                    __recursive_check(k, list(expected.keys())[0], original)
                for v in val.values():
                    __recursive_check(v, list(expected.values())[0], original)
            else:
                if not isinstance(val, expected):
                    __raise_type_error(attr, type(self), original, type(val))

        if attr in self.__types__:
            expected = self.__types__[attr]
            __recursive_check(val, expected, expected)

        setattr(self, attr, val)

    def __eq__(self, other):
        result = self._equal(other)

        self_id = id(self)
        other_id = id(self)
        if self_id in CHECKED_IDS:
            CHECKED_IDS.remove(self_id)
        if other_id in CHECKED_IDS:
            CHECKED_IDS.remove(other_id)

        return result

    def _equal(self, other):
        """
        Equals method to account for circular references where an attribute
        could refer back to itself.
        """
        # Same types
        if not isinstance(other, type(self)):
            return False

        # Same attributes
        if self.__attrs__ != other.__attrs__:
            return False

        # Get ids and save them
        self_id = id(self)
        if self_id not in CHECKED_IDS:
            CHECKED_IDS.add(self_id)
        other_id = id(self)
        if other_id not in CHECKED_IDS:
            CHECKED_IDS.add(other_id)

        # Check attribute values
        for attr in self.__attrs__:
            self_val = getattr(self, attr)
            if id(self_val) in CHECKED_IDS:
                continue

            other_val = getattr(other, attr)
            if id(other_val) in CHECKED_IDS:
                continue

            if self_val != other_val:
                return False

        return True

    def __ne__(self, other):
        return not (self == other)

    def all_attrs(self):
        return self.__slots__

    def dict(self):
        return {a: getattr(self, a) for a in self.all_attrs()}
