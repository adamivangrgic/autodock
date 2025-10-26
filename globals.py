from typing import Dict, Any
import yaml
import json
import os

CONFIG_FILE_PATH = "/config/config.yaml"
REPO_DATA_PATH = "/repo_data"
REPO_DATA_FILE_PATH = "/repo_data/repo_data.json"

HOST_ADDRESS = os.environ.get('HOST_ADDRESS', 'localhost')

repo_data = {}
config_data = {}


def read_yaml_file(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
        print(f"YAML read: {data}")
        return data
    except:
        print("YAML read: failed")
        return None

def read_json_file(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        print(f"JSON read: {data}")
        return data
    except:
        print("JSON read: failed")
        return None

def write_json_file(file_path: str, data):
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=2)
        print(f"JSON write: {data}")
        return True
    except:
        print("JSON write: failed")
        return False