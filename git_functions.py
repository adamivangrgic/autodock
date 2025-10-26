import os

import globals

from subprocess_functions import get_remote_hash, clone_repo, pull_repo, run_command


def git_clone(name: str, url: str, branch: str):
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)

    print(f"TASK ({name}) : first instance, cloning repository.")
    clone_repo(url, repo_dir, branch)


def git_pull(name: str):
    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)

    print(f"TASK ({name}) : first instance, cloning repository.")
    pull_repo(repo_dir)


def git_check(name: str, url: str, branch: str, build_command: str, deploy_command: str):
    print(f"TASK ({name}) : running git check task")

    if name not in globals.repo_data:
        globals.repo_data[name] = {
            'stages': {
                'update': None,
                'build': None,
                'deploy': None
            }
        }
    
    new_hash = get_remote_hash(url, branch)
    
    print(f"TASK ({name}) : \n  old:'{globals.repo_data[name]['stages']['update']}'\n  new:'{new_hash}'")

    repo_dir = os.path.join(globals.REPO_DATA_PATH, name)

    ## update stage (clone or pull)

    if globals.repo_data[name]['stages']['update'] == new_hash:
        print(f"TASK ({name}) : skipping updating.")
    
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

    if globals.repo_data[name]['stages']['build'] == new_hash:
        print(f"TASK ({name}) : skipping building.")
    
    else:
        print(f"TASK ({name}) : executing build command.")
        run_command(build_command, repo_dir)

        globals.repo_data[name]['stages']['build'] = new_hash
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)

    ## deploy stage

    if globals.repo_data[name]['stages']['deploy'] == new_hash:
        print(f"TASK ({name}) : skipping deploying.")
    
    else:
        print(f"TASK ({name}) : executing deploy command.")
        run_command(deploy_command, repo_dir)

        globals.repo_data[name]['stages']['deploy'] = new_hash
        globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)

    ##
        
    print(f"TASK ({name}) : finished.")