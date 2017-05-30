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
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)

        # Combine the slotted class attrs of parent classes
        cls.__slots__ = namespace.get("__slots__", tuple())
        cls.__types__ = namespace.get("__types__", {})
        cls.__defaults__ = namespace.get("__defaults__", {})

        # Check types
        assert isinstance(cls.__slots__, tuple)
        assert isinstance(cls.__types__, dict)
        assert isinstance(cls.__defaults__, dict)

        for base in bases:
            slots = getattr(base, "__slots__", tuple())
            cls.__slots__ = slots + cls.__slots__

            types = getattr(base, "__types__", {})
            cls.__types__.update(types)

            defaults = getattr(base, "__defaults__", {})
            cls.__defaults__.update(defaults)

        # Check slotted attributes
        for attr in cls.__types__:
            assert attr in cls.__slots__, "type '{}' not in __slots__ for {}".format(attr, cls)
        for attr in cls.__defaults__:
            assert attr in cls.__slots__, "default '{}' not in __slots__ for {}".format(attr, cls)


class SlottedClass(metaclass=SlottedClassChecker):
    __slots__ = tuple()
    __types__ = {}
    __defaults__ = {}

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
        if self.__slots__ != other.__slots__:
            return False

        # Get ids and save them
        self_id = id(self)
        if self_id not in CHECKED_IDS:
            CHECKED_IDS.add(self_id)
        other_id = id(self)
        if other_id not in CHECKED_IDS:
            CHECKED_IDS.add(other_id)

        # Check attribute values
        for attr in self.__slots__:
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
