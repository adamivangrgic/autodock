import os
import json
from typing import Dict, Any, Annotated

from fastapi import FastAPI, Request, Form, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import globals
from globals import log, filter_log

from functions import git_check, git_clone, git_pull, docker_container_action, docker_container_inspect

from subprocess_functions import poll_output

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

import asyncio


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def load_config_file(file_path):
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

def write_and_reload_config_file(file_path=globals.CONFIG_FILE_PATH, data=globals.config_data):
    # globals.write_yaml_file(file_path, data)
    # configuration()
    pass

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
async def api_repo_clone(payload: dict, response: Response):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    url = repo['repo_url']
    branch = repo['branch']

    try:
        # await git_clone(name, url, branch)
        asyncio.to_thread(
            git_clone,
            name,
            url,
            branch
        )
        return {'message': 'OK'}
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {'message': e}

@app.post("/api/repo/pull/")
async def api_repo_pull(payload: dict):
    name = payload['name']
    # await git_pull(name)
    await asyncio.to_thread(
        git_pull,
        name
    )

    return {'message': 'OK'}

@app.post("/api/repo/check/")
async def api_repo_check(payload: dict, force: bool = False):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    url = repo['repo_url']
    branch = repo['branch']
    build_command = repo['build_command']
    deploy_command = repo['deploy_command']

    # await git_check(name, url, branch, build_command, deploy_command, ignore_hash_checks=force)
    await asyncio.to_thread(
        git_check,
        name,
        url,
        branch,
        build_command,
        deploy_command,
        ignore_hash_checks=force
    )

    return {'message': 'OK'}

@app.post("/api/repo/build/")
async def api_repo_build(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    build_command = repo['build_command']
    
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)

    def log_callback(line):
        log(line, keyword=name, print_message=False)

    # await poll_output(build_command, repo_dir, callback=log_callback)
    await asyncio.to_thread(
        poll_output,
        build_command,
        repo_dir,
        callback=log_callback
    )

    return {'message': 'OK'}

@app.post("/api/repo/deploy/")
async def api_repo_deploy(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    deploy_command = repo['deploy_command']
    
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)

    def log_callback(line):
        log(line, keyword=name, print_message=False)

    # await poll_output(deploy_command, repo_dir, callback=log_callback)
    await asyncio.to_thread(
        poll_output,
        deploy_command,
        repo_dir,
        callback=log_callback
    )

    return {'message': 'OK'}

@app.post("/api/repo/get_logs/")
async def api_repo_get_logs(payload: dict):
    name = payload['name']
    output = filter_log(name)

    return output

# container

@app.post("/api/container/{action}/")
async def api_container_action(action, payload: dict, response: Response):
    # name = payload['name']
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
    
    try:
        # await docker_container_action(action, container_id)
        await asyncio.to_thread(
            docker_container_action,
            action,
            container_id
        )
        return {'message': 'OK'}
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {'message': e}

## dashboard

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dash_index(request: Request):
    content = globals.config_data['repos']
    
    for name, repo in globals.config_data['repos'].items():
        raw_output, inspect_output = docker_container_inspect(name)
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
    
    raw_output, inspect_output = docker_container_inspect(name)
    content['inspect'] = inspect_output

    return templates.TemplateResponse(
        request=request, name="details.html", 
        context={
            "name": name,
            "repo": content, 
            "HOST_ADDRESS": globals.config_data['host_address'],
            "raw_inspect": raw_output,
            "log_output": filter_log(name)
            }
    )

@app.get("/config/edit/{name}/", response_class=HTMLResponse)
async def dash_config_save(name, request: Request):
    if name != 'new_repo_config':
        content = globals.config_data['repos'][name]
    else:
        content = {
            'repo_url': '',
            'branch': '',
            'interval': '',
            'build_command': '',
            'deploy_command': '',
        }

    return templates.TemplateResponse(
        request=request, name="edit_config.html", 
        context={
            "name": name,
            "repo": content
            }
    )

@app.post("/config/save/", response_class=RedirectResponse)
async def dash_config_save(
        name: Annotated[str, Form()],
        repourl: Annotated[str, Form()],
        branch: Annotated[str, Form()],
        interval: Annotated[str, Form()],
        buildcmd: Annotated[str, Form()],
        deploycmd: Annotated[str, Form()],
    ):

    content = {
        'repo_url': repourl,
        'branch': branch,
        'interval': interval,
        'build_command': buildcmd,
        'deploy_command': deploycmd,
    }

    globals.config_data['repos'][name] = content
    write_and_reload_config_file()

    return RedirectResponse(url=f"/config/edit/{name}/", status_code=status.HTTP_302_FOUND)

@app.get("/config/delete/{name}/", response_class=RedirectResponse)
async def dash_config_delete(name):
    globals.config_data['repos'].pop(name, None)
    write_and_reload_config_file()

    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

##

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)