import os

import json

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import globals

from git_functions import git_check, git_clone, git_pull

from subprocess_functions import run_command, check_output

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():

    globals.config_data = globals.read_yaml_file(globals.CONFIG_FILE_PATH)
    if not globals.config_data:
        # stop startup if no config
        print(f"STARTUP: {globals.CONFIG_FILE_PATH} doesn't exist, aborting startup")
        return None

    if len(globals.config_data['repos']) == 0:
        # stop startup if no repos in json
        print(f"STARTUP: no repositories found in {globals.CONFIG_FILE_PATH}, aborting startup")
        return None

    globals.repo_data = globals.read_json_file(globals.REPO_DATA_FILE_PATH)

    if not globals.repo_data:
        print(f"STARTUP: writing empty repo data file to {globals.REPO_DATA_FILE_PATH}")
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

            print(f"STARTUP: scheduler task configured for {name}, interval {repo['interval']} seconds")
    
    scheduler.start()
    print("STARTUP: scheduler started")

## api endpoints

@app.post("/api/repo/clone/")
async def api_repo_clone(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    url = repo['repo_url']
    branch = repo['branch']
    
    git_clone(name, url, branch)

@app.post("/api/repo/pull/")
async def api_repo_pull(payload: dict):
    name = payload['name']
    
    git_pull(name)

@app.post("/api/repo/check/")
async def api_repo_check(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    url = repo['repo_url']
    branch = repo['branch']
    build_command = repo['build_command']
    deploy_command = repo['deploy_command']
    
    git_check(name, url, branch, build_command, deploy_command)

@app.post("/api/repo/build/")
async def api_repo_build(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    build_command = repo['build_command']
    
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)
    
    run_command(build_command, repo_dir)

@app.post("/api/repo/deploy/")
async def api_repo_deploy(payload: dict):
    name = payload['name']
    repo = globals.config_data['repos'][name]
    deploy_command = repo['deploy_command']
    
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)
    
    run_command(deploy_command, repo_dir)

## dashboard

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dash_index(request: Request):
    content = globals.config_data['repos']
    
    for name, repo in globals.config_data['repos'].items():
        cmd = f"docker inspect {name}"
        raw_output = check_output(cmd)
        inspect_output = json.loads(raw_output)

        content[name]['inspect'] = inspect_output

    return templates.TemplateResponse(
        request=request, name="index.html", context={"content": content}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)