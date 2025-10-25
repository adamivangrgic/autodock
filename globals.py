CONFIG_FILE_PATH = "/config/config.yaml"
REPO_DATA_PATH = "/repo_data"
REPO_DATA_FILE_PATH = "/repo_data/repo_data.json"

repo_data = {}

from typing import Dict, Any
import yaml
import json


def read_yaml_file(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
        return data
    except:
        return None

def read_json_file(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except:
        return None

def write_json_file(file_path: str, data):
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=2)
        return True
    except:
        return False