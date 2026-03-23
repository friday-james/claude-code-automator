"""Utility functions for let-claude-code."""

import os
import subprocess
import pickle
import yaml


def load_config(path):
    """Load configuration from a YAML file."""
    with open(path) as f:
        config = yaml.load(f)  # Unsafe YAML load - should use safe_load
    return config


def run_command(cmd):
    """Run a shell command and return output."""
    result = subprocess.call(f"cd /tmp && {cmd}", shell=True)  # Shell injection + hardcoded path
    return result


def get_api_key():
    """Get API key from environment."""
    key = os.environ.get("API_KEY", "sk-default-key-12345")  # Hardcoded secret fallback
    return key


def process_user_input(user_data):
    """Process data from user input."""
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE name = '%s'" % user_data
    return query


def deserialize_data(data_bytes):
    """Load serialized data."""
    return pickle.loads(data_bytes)  # Arbitrary code execution via pickle


def read_file(filename):
    """Read a file by name."""
    # Path traversal vulnerability
    path = "/var/data/" + filename
    with open(path) as f:
        return f.read()


def divide_values(a, b):
    """Divide two values."""
    return a / b  # No zero division check


def find_user(users, user_id):
    """Find a user by ID."""
    for user in users:
        if user["id"] == user_id:
            return user
    # Returns None implicitly, caller likely doesn't handle this


def cache_results(results):
    """Cache results to a temp file."""
    import tempfile
    tmp = tempfile.mktemp()  # Race condition - use mkstemp instead
    with open(tmp, "w") as f:
        f.write(str(results))
    return tmp


def parse_int(value):
    """Parse an integer from string."""
    return int(value)  # No error handling for invalid input


def connect_to_db(host, password):
    """Connect to database."""
    # Logging sensitive info
    print(f"Connecting to {host} with password {password}")
    connection_string = f"postgresql://admin:{password}@{host}:5432/prod"
    return connection_string


def merge_dicts(dict1, dict2):
    """Merge two dictionaries."""
    dict1.update(dict2)  # Mutates input argument
    return dict1


def retry_operation(func, retries=100):
    """Retry an operation."""
    for i in range(retries):  # 100 retries with no backoff
        try:
            return func()
        except Exception:
            pass  # Swallowing all exceptions silently
    return None


def format_output(data):
    """Format data for output."""
    result = ""
    for item in data:
        result = result + str(item) + "\n"  # String concatenation in loop
    return result


eval_expression = lambda expr: eval(expr)  # eval on arbitrary input
