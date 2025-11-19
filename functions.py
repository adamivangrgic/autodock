import asyncio
import subprocess

import globals
from globals import log

from subprocess_functions import run_command, check_output, poll_output
from git_functions import get_remote_hash, git_clone, git_pull

#   repo build, deploy, health

async def repo_build(name, new_hash=None):
    repo = globals.config_data['repos'][name]
    repo_data = globals.repo_data[name]

    build_command_template = repo['build_command']
    version_tag_scheme = repo['version_tag_scheme']

    version = version_tag_scheme.format(
        name = name,
        build_number = repo_data['build_number']
        )
    build_command = build_command_template.format(
        version_tag_scheme = version, 
        name = name
        )
    
    log(f"Executing build command: {build_command}", keyword=name)

    def log_callback(line):
        log(line, keyword=name, print_message=False)

    await poll_output(build_command, callback=log_callback)

    if new_hash:
        repo_data['stages']['build'] = new_hash

    repo_data['version_history'].append(version)
    repo_data['build_number'] += 1
    globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)


async def repo_deploy(name, deploy_version=None, new_hash=None):
    repo = globals.config_data['repos'][name]
    repo_data = globals.repo_data[name]

    deploy_command_template = repo['deploy_command']
    version_tag_scheme = repo['version_tag_scheme']
    port = repo['port']

    version = deploy_version if deploy_version else version_tag_scheme.format(
        name=name,
        build_number=repo_data['build_number']
    )
    deploy_command = deploy_command_template.format(
        version_tag_scheme=version,
        name=name,
        port=port,
        host_address=globals.config_data['host_address']
    )

    log(f"Executing deploy command: {deploy_command}", keyword=name)

    def log_callback(line):
        log(line, keyword=name, print_message=False)

    await poll_output(deploy_command, callback=log_callback)

    if new_hash:
        repo_data['stages']['deploy'] = new_hash
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)
    

async def repo_healthcheck(name):
    repo = globals.config_data['repos'][name]
    
    port = repo['port']
    command_template = repo['healthcheck']['command']
    timeout = repo['healthcheck']['timeout']
    retries = repo['healthcheck']['retries']
    retry_delay = repo['healthcheck']['retry_delay']
    
    command = command_template.format(
        port=port,
        host_address=globals.config_data['host_address']
    )

    log(f"Executing healthcheck: {command}", keyword=name)

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


async def repo_rollback(name):
    repo_data = globals.repo_data[name]

    if len(repo_data['version_history']) > 1:
        previous_version = repo_data['version_history'][-2]
        
        repo_data['build_number'] -= 1
        repo_data['version_history'].pop()
        
        log(f"Rolling back to version: {previous_version}", keyword=name)
        await repo_deploy(name, previous_version)
        
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)

    else:
        log(f"No previous version to rollback to", keyword=name)

## check

async def repo_check(name, ignore_hash_checks=False):
    repo = globals.config_data['repos'][name]
    repo_data = globals.repo_data[name]

    url = repo['repo_url']
    branch = repo['branch']
    healthcheck_template = repo['healthcheck']['command']

    log(f"Running git check task.", keyword=name)
    
    new_hash = await get_remote_hash(url, branch)
    log(f"Hash comparison: \n  old: '{repo_data['stages']['update']}'\n  new: '{new_hash}'", keyword=name)

    ## update stage (clone or pull)

    if not ignore_hash_checks and repo_data['stages']['update'] == new_hash:
        log(f"Skipping updating.", keyword=name)
    
    else:
        if repo_data['stages']['update'] == None:
            # never cloned, clone entire repo
            await git_clone(name)
        else:
            # otherwise pull changes
            await git_pull(name)
        
        repo_data['stages']['update'] = new_hash
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)
    
    ## build stage

    if not ignore_hash_checks and repo_data['stages']['build'] == new_hash:
        log(f"Skipping building.", keyword=name)
    else:
        await repo_build(name)

    ## deploy stage

    if not ignore_hash_checks and repo_data['stages']['deploy'] == new_hash:
        log(f"Skipping deployment.", keyword=name)
    else:
        await repo_deploy(name)

    ## healthcheck

    if healthcheck_template:
        healthy = await repo_healthcheck(name)

        if not healthy:
            log(f"Health check failed", keyword=name)
            await repo_rollback(name)
    ##
    log(f"Task finished.", keyword=name)