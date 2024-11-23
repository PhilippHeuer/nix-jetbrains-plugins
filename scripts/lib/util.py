from json import load, dumps
import json
import os


def serialize_to_file(data, filename):
    with open(filename, 'w') as file:
        file.write(json.dumps(data, indent=2))
        file.write("\n")


def deserialize_from_file(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return None
