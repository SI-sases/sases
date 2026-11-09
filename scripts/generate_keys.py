import os
import sys
import random
import sqlite3
import string
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "users.db")

CHARS = string.ascii_uppercase + string.digits


def gen_key():
    parts = []
    for _ in range(3):
        seg = "".join(random.choice(CHARS) for _ in range(4))
        parts.append(seg)
    return "SASES-" + "-".join(parts)
