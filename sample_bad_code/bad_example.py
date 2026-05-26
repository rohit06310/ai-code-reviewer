"""
bad_example.py
--------------
Intentionally flawed Python file used to test the AI Code Reviewer pipeline.

Submit this file in a pull request to verify that the reviewer catches real
issues.  Every problem here is deliberate — do not fix them manually before
running the reviewer.
"""

import os
import sys
import json
import hashlib


# ── 1. Hardcoded secret (security: error) ────────────────────────────────────
API_KEY = "sk-prod-abc123supersecretkey"   # never hard-code credentials


# ── 2. Mutable default argument (logic: error) ───────────────────────────────
def add_user(name, users=[]):              # mutable default shares state across calls
    users.append(name)
    return users


# ── 3. Broad exception swallowing (warning) ──────────────────────────────────
def read_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:                                # bare except hides all errors silently
        pass


# ── 4. SQL injection via string formatting (security: error) ─────────────────
def get_user(conn, username):
    query = "SELECT * FROM users WHERE name = '%s'" % username   # use parameterised queries
    return conn.execute(query)


# ── 5. Unused variable + shadowing a builtin (warning) ───────────────────────
def process_items(items):
    list = []                              # shadows builtin 'list'
    result = None                          # assigned but never used
    for i in items:
        list.append(i * 2)
    return list


# ── 6. Unreachable code (error) ──────────────────────────────────────────────
def get_status(code):
    if code == 200:
        return "OK"
        print("This line never runs")     # dead code after return
    return "Error"


# ── 7. Integer division truncation (logic: warning) ──────────────────────────
def average(numbers):
    return sum(numbers) / len(numbers)    # fine in Python 3, but no zero-length guard


def average_safe(numbers):
    total = 0
    for n in numbers:
        total = total + n
    return total / len(numbers)           # still no guard for empty list → ZeroDivisionError


# ── 8. Comparing to None with == (suggestion) ────────────────────────────────
def is_empty(value):
    if value == None:                     # should use 'is None'
        return True
    return False


# ── 9. Missing type hints and docstring (suggestion) ─────────────────────────
def calculate_discount(price, pct):
    return price - (price * pct / 100)


# ── 10. Resource leak — file not closed on exception (warning) ───────────────
def write_report(filename, data):
    f = open(filename, "w")              # should use 'with open(...)' context manager
    f.write(str(data))
    f.close()                            # never reached if f.write() raises


# ── Test trigger ─────────────────────────────────────────────────────────────
print("test")                            # debug print left in production code
