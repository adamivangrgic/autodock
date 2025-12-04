import os
from typing import Annotated
from copy import deepcopy
import asyncio

from fastapi import FastAPI, Request, Form, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware

import globals
from globals import log, filter_log

from functions import repo_build, repo_deploy, repo_healthcheck, repo_check
from git_functions import git_clone, git_pull, get_remote_hash
from docker_functions import docker_container_action, docker_container_inspect, docker_container_get_logs, docker_container_list, docker_image_action, docker_image_list
from config import CONFIG_FILE_REPO_STRUCT, scheduler, write_and_reload_config_file, configuration


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

trusted_host = os.getenv("TRUSTED_HOST", "*")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[trusted_host])

@app.on_event("startup")
async def startup_event():
    configuration()
    scheduler.start()


##  api endpoints

@app.post("/api/repo/check")
async def api_repo_check(payload: dict, force: bool = False):
    name = payload['name']
    await repo_check(name, force)

    return {'message': 'OK'}

@app.post("/webhook/{name}")
async def webhook_repo_check(name, response: Response):
    if name not in globals.config_data['repos']:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {'message': 'Repository not found'}
    
    asyncio.create_task(
        repo_check(name)
    )
    return {'message': 'Webhook received'}

#   repo

@app.post("/api/repo/clone")
async def api_repo_clone(payload: dict, response: Response):
    name = payload['name']

    try:
        await git_clone(name)
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
    await repo_build(name)

    return {'message': 'OK'}

@app.post("/api/repo/deploy")
async def api_repo_deploy(payload: dict):
    name = payload['name']
    tag = payload.get('tag', None)
    await repo_deploy(name, deploy_version=tag)

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

#   images

@app.post("/api/image/action/{action}")
async def api_image_action(action, payload: dict, response: Response):
    image_id = payload['id']

    allowed_actions = [
        'rm'
    ]

    if action not in allowed_actions:
        return None
    
    try:
        await docker_image_action(action, image_id)
        return {'message': 'OK'}
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {'message': e}

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
    images = await docker_image_list(name)

    return templates.TemplateResponse(
        request=request, name="repo_details.html", 
        context={
            "name": name,
            "repo": repo,
            "container": container,
            "images": images,
            "HOST_ADDRESS": globals.config_data['host_address']
            }
    )

@app.get("/repo/edit/{name}", response_class=HTMLResponse)
async def dash_repo_save(name, request: Request):
    if name != 'new_repo_config':
        content = globals.config_data['repos'][name]
    else:
        content = CONFIG_FILE_REPO_STRUCT

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
        repo_url: Annotated[str, Form()],
        branch: Annotated[str, Form()],
        interval: Annotated[int, Form()],
        version_tag_scheme: Annotated[str, Form()],
        build_command: Annotated[str, Form()],
        deploy_command: Annotated[str, Form()],
        healthcheck_command: Annotated[str, Form()],
        port: Annotated[int, Form()],
    ):

    name = name.strip()

    content = CONFIG_FILE_REPO_STRUCT
    content['repo_url'] = repo_url
    content['branch'] = branch
    content['interval'] = interval
    content['version_tag_scheme'] = version_tag_scheme
    content['build_command'] = build_command
    content['deploy_command'] = deploy_command
    content['healthcheck']['command'] = healthcheck_command
    content['port'] = port

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