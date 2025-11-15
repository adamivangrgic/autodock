import os
import json
import asyncio

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
        raise Exception("Repository already exists.")


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


async def git_check(name: str, url: str, branch: str, build_command: str, deploy_command: str, ignore_hash_checks=False):
    log(f"Running git check task.", keyword=name)

    if name not in globals.repo_data:
        globals.repo_data[name] = {
            'stages': {
                'update': None,
                'build': None,
                'deploy': None
            }
        }
    
    new_hash = await get_remote_hash(url, branch)
    
    log(f"Hash comparison: \n  old: '{globals.repo_data[name]['stages']['update']}'\n  new: '{new_hash}'", keyword=name)

    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)

    ## update stage (clone or pull)

    if not ignore_hash_checks and globals.repo_data[name]['stages']['update'] == new_hash:
        log(f"Skipping updating.", keyword=name)
    
    else:
        if globals.repo_data[name]['stages']['update'] == None:
            # never cloned, clone entire repo
            await git_clone(name, url, branch)
        else:
            # otherwise pull changes
            await git_pull(name)
        
        globals.repo_data[name]['stages']['update'] = new_hash
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)
    
    ## build stage

    def log_callback(line):
        log(line, keyword=name, print_message=False)


    if not ignore_hash_checks and globals.repo_data[name]['stages']['build'] == new_hash:
        log(f"Skipping building.", keyword=name)
    
    else:
        log(f"Executing build command.", keyword=name)
        await poll_output(build_command, repo_dir, callback=log_callback)

        globals.repo_data[name]['stages']['build'] = new_hash
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)

    ## deploy stage

    if not ignore_hash_checks and globals.repo_data[name]['stages']['deploy'] == new_hash:
        log(f"Skipping deployment.", keyword=name)
    
    else:
        log(f"Executing deploy command.", keyword=name)
        await poll_output(deploy_command, repo_dir, callback=log_callback)

        globals.repo_data[name]['stages']['deploy'] = new_hash
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)

    ##
        
    log(f"Task finished.", keyword=name)

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

    try:
        output = await asyncio.to_thread(check_output, cmd)
    except Exception as e:
        output = None
        print(e)

    return output