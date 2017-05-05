import unittest

from cparse import Parser
from lang_ast import *

PARSER = Parser()


class TestExamples(unittest.TestCase):
    def __create_ast(self, filename):
        with open(filename, "r") as f:
            return PARSER.parse(f.read())

    def test_examples(self):
        ast = self.__create_ast("examples/examples.py")

    def test_hello_world(self):
        ast = self.__create_ast("examples/hello_world.py")


if __name__ == "__main__":
    unittest.main()
