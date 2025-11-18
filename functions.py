import os
import json
import asyncio
import subprocess

import globals
from globals import log

from subprocess_functions import run_command, check_output, poll_output


## git

async def git_clone(name: str, url: str, branch: str):
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)

    log(f"Cloning into repo {url} {branch}", keyword=name)

    if not os.path.exists(os.path.join(repo_dir, ".git")):
        cmd = f"git clone --branch {branch} --single-branch {url} {repo_dir}"

        def log_callback(line):
            log(line, keyword=name, print_message=False)

        await poll_output(cmd, callback=log_callback)

        log("Repo successfully cloned.", keyword=name)
    else:
        log("Repository already exists.", keyword=name)
        # raise Exception("Repository already exists.")


async def git_pull(name: str):
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)

    log(f"Pulling repo {repo_dir}", keyword=name)

    cmd = "git pull --rebase"

    def log_callback(line):
        log(line, keyword=name, print_message=False)
        
    await poll_output(cmd, repo_dir, callback=log_callback)

    log("Repo successfully pulled.")


async def get_remote_hash(url, branch='main'):
    log(f"Getting {url} {branch} hash")

    cmd = f"git ls-remote {url} refs/heads/{branch}"
    result = await asyncio.to_thread(check_output, cmd)

    return result.split()[0] if result else None

#   repo build, deploy, health

async def repo_build(name, version, build_command, new_hash=None):
    def log_callback(line):
        log(line, keyword=name, print_message=False)

    await poll_output(build_command, callback=log_callback)

    if new_hash:
        globals.repo_data[name]['stages']['build'] = new_hash

    globals.repo_data[name]['version_history'].append(version)
    globals.repo_data[name]['build_number'] += 1
    globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)


async def repo_deploy(name, deploy_command, new_hash=None):
    def log_callback(line):
        log(line, keyword=name, print_message=False)

    await poll_output(deploy_command, callback=log_callback)

    if new_hash:
        globals.repo_data[name]['stages']['deploy'] = new_hash
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)
    

async def repo_healthcheck(name, command, timeout=30, retries=3, retry_delay=5):
    for attempt in range(retries):
        await asyncio.sleep(retry_delay)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await asyncio.wait_for(process.wait(), timeout=timeout)
            
            return process.returncode == 0
            
        except (asyncio.TimeoutError, subprocess.CalledProcessError) as e:
            log(f"Health check attempt {attempt + 1} failed: {e}", keyword=name)

## docker

async def docker_container_action(action, container_id):
    cmd = f"docker {action} {container_id}"
    await asyncio.to_thread(run_command, cmd)
        
async def docker_container_inspect(name):
    cmd = f"docker inspect --type=container {name}"

    try:
        raw_output = await asyncio.to_thread(check_output, cmd)
        inspect_output = json.loads(raw_output)
    except Exception as e:
        raw_output = None
        inspect_output = None
        print(e)

    return raw_output, inspect_output
    
async def docker_container_get_logs(container_id, num_of_lines=100):
    cmd = f"docker logs -n {num_of_lines} {container_id}"
    output = await asyncio.to_thread(check_output, cmd)

    return output

async def docker_container_list():
    cmd = 'docker ps -a --no-trunc --format "{{.ID}};{{.Names}};{{.State}};{{.CreatedAt}};{{.Ports}};{{.Image}}"'
    raw_otput = await asyncio.to_thread(check_output, cmd)

    string_list = raw_otput.split('\n')
    output = []

    for string in string_list:
        if string:
            values = string.split(';')
            
            output.append({
                'Id': values[0],
                'Names': values[1],
                'State': values[2],
                'CreatedAt': values[3],
                'Ports': values[4].split(', '),
                'Image': values[5],
            })

    return output

async def docker_image_list(repo_filter=None):
    cmd = 'docker image ls --no-trunc --format "{{.ID}};{{.Repository}};{{.Tag}};{{.CreatedAt}};{{.Size}}"'
    raw_otput = await asyncio.to_thread(check_output, cmd)

    string_list = raw_otput.split('\n')
    output = []

    for string in string_list:
        if string:
            values = string.split(';')

            if not repo_filter or repo_filter == values[1]:
                output.append({
                    'Id': values[0],
                    'Repository': values[1],
                    'Tag': values[2],
                    'CreatedAt': values[3],
                    'Size': values[4],
                })

    return output