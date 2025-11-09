import os

import globals
from globals import log

from subprocess_functions import get_remote_hash, clone_repo, pull_repo, run_command, poll_output


def git_clone(name: str, url: str, branch: str):
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)

    log(f"Cloning repository.", keyword=name)
    clone_repo(url, repo_dir, branch)


def git_pull(name: str):
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)

    log(f"Pulling repository.", keyword=name)
    pull_repo(repo_dir)


async def git_check(name: str, url: str, branch: str, build_command: str, deploy_command: str):
    log(f"Running git check task.", keyword=name)

    if name not in globals.repo_data:
        globals.repo_data[name] = {
            'stages': {
                'update': None,
                'build': None,
                'deploy': None
            }
        }
    
    new_hash = get_remote_hash(url, branch)
    
    log(f"Hash comparison: \n  old: '{globals.repo_data[name]['stages']['update']}'\n  new: '{new_hash}'", keyword=name)

    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)

    ## update stage (clone or pull)

    if globals.repo_data[name]['stages']['update'] == new_hash:
        log(f"Skipping updating.", keyword=name)
    
    else:
        if globals.repo_data[name]['stages']['update'] == None:
            # never cloned, clone entire repo
            git_clone(name, url, branch)
        else:
            # otherwise pull changes
            git_pull(name)
        
        globals.repo_data[name]['stages']['update'] = new_hash
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)
    
    ## build stage
    
    def log_callback(line):
        log(line, keyword=name, print_message=False)


    if globals.repo_data[name]['stages']['build'] == new_hash:
        log(f"Skipping building.", keyword=name)
    
    else:
        log(f"Executing build command.", keyword=name)
        # run_command(build_command, repo_dir)
        await poll_output(build_command, repo_dir, callback=log_callback)

        globals.repo_data[name]['stages']['build'] = new_hash
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)

    ## deploy stage

    if globals.repo_data[name]['stages']['deploy'] == new_hash:
        log(f"Skipping deploying.", keyword=name)
    
    else:
        log(f"Executing deploy command.", keyword=name)
        # run_command(deploy_command, repo_dir)
        await poll_output(deploy_command, repo_dir, callback=log_callback)

        globals.repo_data[name]['stages']['deploy'] = new_hash
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)

    ##
        
    log(f"Task finished.", keyword=name)