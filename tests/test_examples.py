import unittest

from cparse import Parser
from lang_ast import *
from compiler import *

PARSER = Parser()


class TestExamples(unittest.TestCase):
    def __create_ast(self, filename):
        with open(filename, "r") as f:
            return PARSER.parse(f.read())

    def test_examples(self):
        ast = self.__create_ast("examples/examples.py")

    def test_hello_world(self):
        ast = self.__create_ast("examples/hello_world.py")

    def test_linked_list(self):
        """Make sure the linked list example compiles and runs."""
        run_files(["examples/linked_list/ll.cu", "examples/linked_list/ll_test.cu"])


if __name__ == "__main__":
    unittest.main()
