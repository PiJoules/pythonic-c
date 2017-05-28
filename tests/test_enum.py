import unittest
import subprocess

from compiler import *


class TestEnum(unittest.TestCase):
    def test_enum_code(self):
        run_files(["examples/test_enum.cu"], stdout=subprocess.PIPE)


if __name__ == "__main__":
    unittest.main()
