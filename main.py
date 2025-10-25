from fastapi import FastAPI

from typing import Dict, Any

import os
import yaml
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
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

async def git_check(name: str, url: str, branch: str, build_command: str, deploy_command: str):
    global repo_data

    if name not in repo_data:
        repo_data[name] = {'latest_hash': None}
    
    latest_hash = repo_data[name]['latest_hash']
    new_hash = get_remote_hash(url, branch)

    if latest_hash == new_hash:             # stop process if hashes are identical
        return None
    
    repo_dir = os.path.join(REPO_DATA_PATH, name)
    
    if latest_hash == None:                 # never cloned, clone entire repo
        clone_repo(url, repo_dir, branch)
    else:
        pull_repo(repo_dir)                 # otherwise pull changes
    
    run_command(build_command, repo_dir)
    
    run_command(deploy_command, repo_dir)

    repo_data[name] = {'latest_hash': new_hash}         # update to new hash after a successful build and deploy process
    write_json_file(REPO_DATA_FILE_PATH, repo_data)


@app.on_event("startup")
async def startup_event():
    global repo_data

    config_data = read_yaml_file(CONFIG_FILE_PATH)

    if not config_data:                     # stop startup if no config
        return None

    repo_data = read_json_file(REPO_DATA_FILE_PATH)

    if not repo_data:
        repo_data = {}
        write_json_file(REPO_DATA_FILE_PATH, repo_data)

    if len(config_data['repos']) == 0:      # stop startup if no repos in json
        return None

    scheduler = AsyncIOScheduler()

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
            id="git_check_periodic_task_" + repo['name'],
            replace_existing=True
        )
    
    scheduler.start()

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