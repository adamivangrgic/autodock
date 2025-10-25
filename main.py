from fastapi import FastAPI

from typing import Dict, Any

import os
import yaml
import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from subprocess_functions import get_remote_hash, clone_repo, pull_repo, run_command


app = FastAPI()

CONFIG_FILE_PATH = "/config/config.yaml"
REPO_DATA_FILE_PATH = "/config/repo_data.json"
REPO_DATA_PATH = "/repo_data"

repo_data = {}


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

def git_check(name: str, url: str, branch: str, build_command: str, deploy_command: str):
    global repo_data

    print(f"TASK ({name}) : running git check task")

    if name not in repo_data:
        repo_data[name] = {'latest_hash': None}
    
    latest_hash = repo_data[name]['latest_hash']
    new_hash = get_remote_hash(url, branch)
    
    print(f"TASK ({name}) : \n  old:'{latest_hash}'\n  new:'{new_hash}'")

    if latest_hash == new_hash:                                                                             # stop process if hashes are identical
        print(f"TASK ({name}) : hashes identical, aborting task.")
        return None
    
    repo_dir = os.path.join(REPO_DATA_PATH, name)
    
    if latest_hash == None:                                                                                 # never cloned, clone entire repo
        print(f"TASK ({name}) : first instance, cloning repository.")
        clone_repo(url, repo_dir, branch)
    else:
        print(f"TASK ({name}) : pulling repository.")
        pull_repo(repo_dir)                                                                                 # otherwise pull changes
    
    print(f"TASK ({name}) : executing build command.")
    run_command(build_command, repo_dir)
    
    print(f"TASK ({name}) : executing deploy command.")
    run_command(deploy_command, repo_dir)

    repo_data[name] = {'latest_hash': new_hash}                                                             # update to new hash after a successful build and deploy process
    write_json_file(REPO_DATA_FILE_PATH, repo_data)


@app.on_event("startup")
async def startup_event():
    global repo_data

    config_data = read_yaml_file(CONFIG_FILE_PATH)
    if not config_data:                                                                                     # stop startup if no config
        print(f"STARTUP: {CONFIG_FILE_PATH} doesn't exist, aborting startup")
        return None

    if len(config_data['repos']) == 0:  
        print(f"STARTUP: no repositories found in {CONFIG_FILE_PATH}, aborting startup")                    # stop startup if no repos in json
        return None

    repo_data = read_json_file(REPO_DATA_FILE_PATH)

    if not repo_data:
        print(f"STARTUP: writing empty repo data file to {REPO_DATA_FILE_PATH}")
        repo_data = {}
        write_json_file(REPO_DATA_FILE_PATH, repo_data)

    scheduler = BackgroundScheduler()

    for repo in config_data['repos']:
        scheduler.add_job(
            git_check,
            args=[
                repo['name'],
                repo['repo_url'],
                repo['branch'],
                repo['build_command'],
                repo['deploy_command'],
            ],
            trigger=IntervalTrigger(seconds=repo['interval']),
            id=f"git_check_periodic_task_{repo['name']}",
            replace_existing=True,
            max_instances=1
        )

        print(f"STARTUP: scheduler task configured for {repo['name']}, interval {repo['interval']} seconds")
    
    scheduler.start()
    print("STARTUP: scheduler started")

# # Define a root endpoint
# @app.get("/")
# def read_root():
#     return {"message": "Hello, World!"}

# # Define an endpoint with path parameter
# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: str = None):
#     return {"item_id": item_id, "q": q}

# # Define a POST endpoint
# @app.post("/items/")
# def create_item(item: dict):
#     return {"received_item": item}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)