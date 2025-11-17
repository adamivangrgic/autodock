import os
import json
from typing import Dict, Any, Annotated
from copy import deepcopy
import asyncio

from fastapi import FastAPI, Request, Form, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware

import globals
from globals import log, filter_log

from functions import repo_check, repo_build, repo_deploy, git_clone, git_pull
from functions import docker_container_action, docker_container_inspect, docker_container_get_logs, docker_container_list, docker_image_list

from subprocess_functions import poll_output

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

scheduler = AsyncIOScheduler()


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

trusted_host = os.getenv("TRUSTED_HOST", "*")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[trusted_host])


def load_config_file(file_path):
    file = globals.read_yaml_file(file_path)

    if not file:
        file = {
            'repos': {},
            'host_address': 'localhost'
        }
        return file

    if 'repos' not in file:
        file['repos'] = {}

    for name, repo in file['repos'].items():
        if 'repo_url' not in repo:
            print(f"CONFIG LOAD: repo_url not found in {name}")
            return {}

        if 'branch' not in repo:
            file['repos'][name]['branch'] = 'main'

        if 'interval' not in repo:
            file['repos'][name]['interval'] = 0

        if 'version_tag_scheme' not in repo:
            file['repos'][name]['version_tag_scheme'] = ''

        if 'build_command' not in repo:
            print(f"CONFIG LOAD: build_command not found in {name}")
            return {}

        if 'deploy_command' not in repo:
            print(f"CONFIG LOAD: deploy_command not found in {name}")
            return {}

    if 'host_address' not in file:
        file['host_address'] = 'localhost'

    return file

def write_and_reload_config_file():
    globals.write_yaml_file(globals.CONFIG_FILE_PATH, globals.config_data)
    configuration()

def configuration():
    globals.repo_data = globals.read_json_file(globals.REPO_DATA_FILE_PATH)
    
    if not globals.repo_data:
        print(f"CONFIGURATION: writing empty repo data file to {globals.REPO_DATA_FILE_PATH}")
        globals.repo_data = {}
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)

    globals.config_data = load_config_file(globals.CONFIG_FILE_PATH)
    if not globals.config_data:
        # stop startup if no config
        print(f"CONFIGURATION: {globals.CONFIG_FILE_PATH} doesn't exist, aborting startup")
        return None

    if len(globals.config_data['repos']) == 0:
        # stop startup if no repos in json
        print(f"CONFIGURATION: no repositories found in {globals.CONFIG_FILE_PATH}, aborting startup")
        return None

    scheduler.remove_all_jobs()
    
    for name, repo in globals.config_data['repos'].items():
        if name not in globals.repo_data:
            globals.repo_data[name] = {
                'stages': {
                    'update': None,
                    'build': None,
                    'deploy': None
                },
                'build_number': 0,
                'version_history': []
            }
        
        if repo['interval'] > 0:
            scheduler.add_job(
                repo_check_trigger,
                args=[name, False],
                trigger=IntervalTrigger(seconds=repo['interval']),
                id=f"repo_check_periodic_task_{name}",
                replace_existing=True,
                max_instances=1,
                next_run_time=datetime.now()
            )

            print(f"CONFIGURATION: scheduler task configured for {name}, interval {repo['interval']} seconds")

    globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)
    
    print("CONFIGURATION: done.")

@app.on_event("startup")
async def startup_event():
    configuration()
    scheduler.start()

##  api endpoints
#   check

async def repo_check_trigger(name, ignore_hash_checks=False):
    repo = globals.config_data['repos'][name]
    url = repo['repo_url']
    branch = repo['branch']
    build_command = repo['build_command']
    deploy_command = repo['deploy_command']
    version_tag_scheme = repo['version_tag_scheme']

    version = version_tag_scheme.format(
        name = name,
        build_number = globals.repo_data[name]['build_number']
        )

    build_command = build_command.format(
        version_tag_scheme = version, 
        name = name
        )
    deploy_command = deploy_command.format(
        version_tag_scheme = version, 
        name = name
        )

    await repo_check(name, url, branch, build_command, deploy_command, version, ignore_hash_checks)

@app.post("/api/repo/check")
async def api_repo_check(payload: dict, force: bool = False):
    name = payload['name']
    await repo_check_trigger(name, force)

    return {'message': 'OK'}

@app.post("/webhook/{name}")
async def webhook_repo_check(name, response: Response):
    if name not in globals.config_data['repos']:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {'message': 'Repository not found'}
    
    asyncio.create_task(
        repo_check_trigger(name)
    )
    return {'message': 'Webhook received'}

#   repo

@app.post("/api/repo/clone")
async def api_repo_clone(payload: dict, response: Response):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    url = repo['repo_url']
    branch = repo['branch']

    try:
        await git_clone(name, url, branch)
        return {'message': 'OK'}
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {'message': e}

@app.post("/api/repo/pull")
async def api_repo_pull(payload: dict):
    name = payload['name']
    await git_pull(name)

    return {'message': 'OK'}

@app.post("/api/repo/build")
async def api_repo_build(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    build_command = repo['build_command']
    version_tag_scheme = repo['version_tag_scheme']

    version = version_tag_scheme.format(
        name = name,
        build_number = globals.repo_data[name]['build_number']
        )
    build_command = build_command.format(
        version_tag_scheme = version, 
        name = name
        )

    await repo_build(name, build_command)

    return {'message': 'OK'}

@app.post("/api/repo/deploy")
async def api_repo_deploy(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    deploy_command = repo['deploy_command']
    version_tag_scheme = repo['version_tag_scheme']

    version = version_tag_scheme.format(
        name = name,
        build_number = globals.repo_data[name]['build_number']
        )
    deploy_command = deploy_command.format(
        version_tag_scheme = version,
        name = name
        )

    await repo_deploy(name, deploy_command)

    return {'message': 'OK'}

@app.post("/api/repo/get_logs")
async def api_repo_get_logs(payload: dict):
    name = payload['name']
    num_of_lines = int(payload.get('line_num', 100))
    output = filter_log(name, num_of_lines)

    return output

#   container

@app.post("/api/container/action/{action}")
async def api_container_action(action, payload: dict, response: Response):
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
        await docker_container_action(action, container_id)
        return {'message': 'OK'}
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {'message': e}

@app.post("/api/container/get_logs")
async def api_container_get_logs(payload: dict):
    container_id = payload['id']
    num_of_lines = payload.get('line_num', 100)
    
    output = await docker_container_get_logs(container_id, num_of_lines)
    return output

## dashboard

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dash_index(request: Request):
    content = deepcopy(globals.config_data['repos'])
    
    for name, repo in globals.config_data['repos'].items():
        raw_output, inspect_output = await docker_container_inspect(name)
        content[name]['inspect'] = inspect_output

    return templates.TemplateResponse(
        request=request, name="index.html", 
        context={
            "content": content, 
            "HOST_ADDRESS": globals.config_data['host_address']
            }
    )

@app.get("/repo/{name}", response_class=HTMLResponse)
async def dash_repo_details(name, request: Request):
    repo = globals.config_data['repos'].get(name, None)
    raw_container_output, container = await docker_container_inspect(name)

    return templates.TemplateResponse(
        request=request, name="repo_details.html", 
        context={
            "name": name,
            "repo": repo,
            "container": container,
            "HOST_ADDRESS": globals.config_data['host_address']
            }
    )

@app.get("/repo/edit/{name}", response_class=HTMLResponse)
async def dash_repo_save(name, request: Request):
    if name != 'new_repo_config':
        content = globals.config_data['repos'][name]
    else:
        content = {
            'repo_url': '',
            'branch': 'main',
            'interval': 0,
            'version_tag_scheme': '{name}:alpha.{build_number}',
            'build_command': 'docker build -t {version_tag_scheme} -t {name}:latest /repo_data/{name}',
            'deploy_command': 'docker rm -f {name} || true && docker run --name {name} -d {version_tag_scheme}',
        }

    return templates.TemplateResponse(
        request=request, name="edit_config.html", 
        context={
            "name": name,
            "repo": content
            }
    )

@app.post("/repo/save", response_class=RedirectResponse)
async def dash_repo_save(
        name: Annotated[str, Form()],
        repourl: Annotated[str, Form()],
        branch: Annotated[str, Form()],
        interval: Annotated[int, Form()],
        version_tag_scheme: Annotated[str, Form()],
        buildcmd: Annotated[str, Form()],
        deploycmd: Annotated[str, Form()],
    ):

    name = name.strip()

    content = {
        'repo_url': repourl,
        'branch': branch,
        'interval': interval,
        'version_tag_scheme': version_tag_scheme,
        'build_command': buildcmd,
        'deploy_command': deploycmd,
    }

    globals.config_data['repos'][name] = content
    write_and_reload_config_file()

    return RedirectResponse(url=f"/repo/{name}", status_code=status.HTTP_302_FOUND)

@app.get("/repo/delete/{name}", response_class=RedirectResponse)
async def dash_repo_delete(name):
    globals.config_data['repos'].pop(name, None)
    write_and_reload_config_file()

    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

@app.get("/containers", response_class=HTMLResponse)
async def dash_containers(request: Request):
    content = await docker_container_list()

    return templates.TemplateResponse(
        request=request, name="containers.html", 
        context={
            "content": content, 
            "HOST_ADDRESS": globals.config_data['host_address']
            }
    )

@app.get("/container/{container_id}", response_class=HTMLResponse)
async def dash_container_details(container_id, request: Request):
    raw_container_output, container = await docker_container_inspect(container_id)

    return templates.TemplateResponse(
        request=request, name="container_details.html", 
        context={
            "container": container,
            "HOST_ADDRESS": globals.config_data['host_address']
            }
    )

@app.get("/images", response_class=HTMLResponse)
async def dash_images(request: Request, repo_filter=None):
    content = await docker_image_list(repo_filter)

    return templates.TemplateResponse(
        request=request, name="images.html", 
        context={
            "content": content
            }
    )

##

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        proxy_headers=True,
        forwarded_allow_ips="*"
        )