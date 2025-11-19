import os
import asyncio

import globals
from globals import log

from subprocess_functions import run_command, check_output, poll_output


async def git_clone(name: str):
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)
    
    repo = globals.config_data['repos'][name]
    url = repo['repo_url']
    branch = repo['branch']

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