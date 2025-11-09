import os
import json
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import globals
from globals import log, filter_log

from git_functions import git_check, git_clone, git_pull

from subprocess_functions import run_command, check_output, poll_output

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

import asyncio


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def load_config_file(file_path: str) -> Dict[str, Any]:
    file = globals.read_yaml_file(file_path)

    for name, repo in file['repos'].items():
        if 'repo_url' not in repo:
            print(f"CONFIG LOAD: repo_url not found in {name}")
            return {}

        if 'branch' not in repo:
            file['repos']['branch'] = 'main'

        if 'interval' not in repo:
            file['repos']['interval'] = 0

        if 'build_command' not in repo:
            print(f"CONFIG LOAD: build_command not found in {name}")
            return {}

        if 'deploy_command' not in repo:
            print(f"CONFIG LOAD: deploy_command not found in {name}")
            return {}

    if 'host_address' not in file:
        file['host_address'] = 'localhost'

    return file

def configuration():
    globals.config_data = load_config_file(globals.CONFIG_FILE_PATH)
    if not globals.config_data:
        # stop startup if no config
        print(f"CONFIGURATION: {globals.CONFIG_FILE_PATH} doesn't exist, aborting startup")
        return None

    if len(globals.config_data['repos']) == 0:
        # stop startup if no repos in json
        print(f"CONFIGURATION: no repositories found in {globals.CONFIG_FILE_PATH}, aborting startup")
        return None

    globals.repo_data = globals.read_json_file(globals.REPO_DATA_FILE_PATH)

    if not globals.repo_data:
        print(f"CONFIGURATION: writing empty repo data file to {globals.REPO_DATA_FILE_PATH}")
        globals.repo_data = {}
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)

    scheduler = BackgroundScheduler()

    for name, repo in globals.config_data['repos'].items():
        if repo['interval'] > 0:
            scheduler.add_job(
                git_check,
                args=[
                    name,
                    repo['repo_url'],
                    repo['branch'],
                    repo['build_command'],
                    repo['deploy_command'],
                ],
                trigger=IntervalTrigger(seconds=repo['interval']),
                id=f"git_check_periodic_task_{name}",
                replace_existing=True,
                max_instances=1,
                next_run_time=datetime.now()
            )

            print(f"CONFIGURATION: scheduler task configured for {name}, interval {repo['interval']} seconds")
    
    scheduler.start()
    print("CONFIGURATION: scheduler started")

@app.on_event("startup")
async def startup_event():
    configuration()

## api endpoints

# repo

@app.post("/api/repo/clone/")
async def api_repo_clone(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    url = repo['repo_url']
    branch = repo['branch']
    
    output = await asyncio.to_thread(
        git_clone,
        name,
        url,
        branch
    )

    return output

@app.post("/api/repo/pull/")
async def api_repo_pull(payload: dict):
    name = payload['name']
    
    output = await asyncio.to_thread(
        git_pull,
        name
    )

    return output

@app.post("/api/repo/check/")
async def api_repo_check(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    url = repo['repo_url']
    branch = repo['branch']
    build_command = repo['build_command']
    deploy_command = repo['deploy_command']
    
    output = await asyncio.to_thread(
        git_check,
        name,
        url,
        branch,
        build_command,
        deploy_command
    )

    return output

@app.post("/api/repo/build/")
async def api_repo_build(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    build_command = repo['build_command']
    
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)
    
    output = await asyncio.to_thread(
        poll_output,
        build_command,
        repo_dir
    )
    
    for line in output:
        log(line, keyword=name, print_message=False)

@app.post("/api/repo/deploy/")
async def api_repo_deploy(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    deploy_command = repo['deploy_command']
    
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)
    
    output = await asyncio.to_thread(
        poll_output,
        deploy_command,
        repo_dir
    )
    
    for line in output:
        log(line, keyword=name, print_message=False)

@app.post("/api/repo/get_logs/")
async def api_repo_get_logs(payload: dict):
    name = payload['name']
    output = filter_log(name)

    return output

# container

@app.post("/api/container/{action}/")
async def api_container_action(action, payload: dict):
    container_id = payload['id']

    allowed_actions = [
        'start',
        'stop',
        'kill',
        'restart',
        'pause',
        'unpause',
        'rm'
    ]

    if action not in allowed_actions:
        return None

    cmd = f"docker {action} {container_id}"
    
    output = await asyncio.to_thread(
        run_command,
        cmd
    )

## dashboard

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dash_index(request: Request):
    content = globals.config_data['repos']
    
    for name, repo in globals.config_data['repos'].items():
        cmd = f"docker inspect --type=container {name}"

        try:
            raw_output = check_output(cmd)
            inspect_output = json.loads(raw_output)
        except:
            inspect_output = None

        content[name]['inspect'] = inspect_output

    return templates.TemplateResponse(
        request=request, name="index.html", 
        context={
            "content": content, 
            "HOST_ADDRESS": globals.config_data['host_address']
            }
    )

@app.get("/details/{name}/", response_class=HTMLResponse)
async def dash_details(name, request: Request):
    content = globals.config_data['repos'][name]
    
    cmd = f"docker inspect --type=container {name}"

    try:
        raw_output = check_output(cmd)
        inspect_output = json.loads(raw_output)
    except:
        raw_output = None
        inspect_output = None

    content['inspect'] = inspect_output

    return templates.TemplateResponse(
        request=request, name="details.html", 
        context={
            "name": name,
            "repo": content, 
            "HOST_ADDRESS": globals.config_data['host_address'],
            "raw_inspect": raw_output
            }
    )

@app.get("/edit_config/{name}/", response_class=HTMLResponse)
async def dash_edit_config(name, request: Request):
    content = globals.config_data['repos'][name]

    return templates.TemplateResponse(
        request=request, name="edit_config.html", 
        context={
            "name": name,
            "repo": content
            }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)