from copy import deepcopy

import globals

from functions import repo_check

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime


scheduler = AsyncIOScheduler()

CONFIG_FILE_STRUCT = {
        'repos': {},
        'host_address': 'localhost'
    }
CONFIG_FILE_REPO_STRUCT = {
        'repo_url': '',
        'branch': 'main',
        'interval': 0,
        'version_tag_scheme': '{name}:v{build_number}',
        'build_command': 'docker build -t {version_tag_scheme} -t {name}:latest /repo_data/{name}',
        'deploy_command': 'docker rm -f {name} || true && docker run --name {name} -p {port}:8080 -d {version_tag_scheme}',
        'healthcheck': {
                'command': 'curl -f {host_address}:{port} || exit 1',
                'timeout': 30,
                'retries': 3,
                'retry_delay': 5
            },
        'port': 8080,
    }

def load_config_file(file_path):
    file = globals.read_yaml_file(file_path)

    if not file:
        return deepcopy(CONFIG_FILE_STRUCT)

    file = CONFIG_FILE_STRUCT | file

    for name, repo in file['repos'].items():
        file['repos'][name] = CONFIG_FILE_REPO_STRUCT | repo

    return file


def write_and_reload_config_file():
    globals.write_yaml_file(globals.CONFIG_FILE_PATH, globals.config_data)
    configuration()


def configuration():
    globals.repo_data = globals.read_json_file(globals.REPO_DATA_FILE_PATH)
    if not globals.repo_data:
        globals.repo_data = {}

    globals.config_data = load_config_file(globals.CONFIG_FILE_PATH)

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
                repo_check,
                args=[name, False],
                trigger=IntervalTrigger(seconds=repo['interval']),
                id=f"repo_check_periodic_task_{name}",
                replace_existing=True,
                max_instances=1,
                next_run_time=datetime.now()
            )

            print(f"CONFIGURATION: scheduler task configured for {name}, interval {repo['interval']} seconds")

    globals.write_json_file(globals.REPO_DATA_FILE_PATH, globals.repo_data)
    
    print("CONFIGURATION: loaded")