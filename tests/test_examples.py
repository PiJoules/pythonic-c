import unittest
import subprocess

from compiler import *


class TestExamples(unittest.TestCase):
    def test_examples(self):
        file_to_ast("examples/examples.cu")

    def test_hello_world(self):
        file_to_ast("examples/hello_world.cu")

    def test_linked_list(self):
        """Make sure the linked list example compiles and runs."""
        run_files(
            ["examples/linked_list/ll.cu", "examples/linked_list/ll_test.cu"],
            stdout=subprocess.PIPE
        )


if __name__ == "__main__":
    unittest.main()
