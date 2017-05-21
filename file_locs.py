import os

from file_conversion import *


SRC_DIR = os.path.abspath(os.path.dirname(__file__))
FAKE_LANG_HEADERS_DIR = os.path.join(SRC_DIR, "FakeLangHeaders")

def __find_system_headers():
    for root, dirs, files in os.walk(FAKE_LANG_HEADERS_DIR):
        for filename in files:
            path = os.path.join(root, filename)

