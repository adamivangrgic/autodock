from typing import Dict, Any
import yaml
import json

CONFIG_FILE_PATH = "/config/config.yaml"
REPO_DATA_PATH = "/repo_data"
REPO_DATA_FILE_PATH = "/repo_data/repo_data.json"
    
repo_data = {}
config_data = {}

##

log_output = {}

def log(message, keyword='default', print_message=True):
    if print_message:
        print(message)

    if keyword not in log_output:
        log_output[keyword] = []

    log_output[keyword].append(message)

def filter_log(keyword, num_of_lines=100):
    if keyword in log_output:
        return "\n".join(log_output[keyword][-num_of_lines:])
    else:
        return ''

##

def read_yaml_file(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
        return data
    except:
        print("YAML read: failed")
        return None

def write_yaml_file(file_path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(file_path, 'w') as file:
            yaml.dump(data, file, default_flow_style=False, indent=2)
        return True
    except Exception as e:
        print(f"YAML write: failed - {e}")
        return False

##

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