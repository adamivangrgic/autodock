from typing import Dict, Any
import yaml
import json

CONFIG_FILE_PATH = "/config/config.yaml"
REPO_DATA_PATH = "/repo_data"
REPO_DATA_FILE_PATH = "/repo_data/repo_data.json"
    
repo_data = {}
config_data = {}

##

log_output = []

def log(log):
    print(log)

    log_output.append(log)

def filter_log(keyword):
    return "\n".join([k for k in log_output if keyword in k])

##

def read_yaml_file(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
        return data
    except:
        print("YAML read: failed")
        return None

def read_json_file(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except:
        print("JSON read: failed")
        return None

def write_json_file(file_path: str, data):
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=2)
        return True
    except:
        print("JSON write: failed")
        return False