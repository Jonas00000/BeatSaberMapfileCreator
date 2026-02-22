import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    # Config lives next to the exe, not inside _internal
    CONFIG_PATH = os.path.join(os.path.dirname(sys.executable), "config.json")
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

BIN_DIR = os.path.join(BASE_DIR, "bin")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
