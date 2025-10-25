from fastapi import FastAPI

from globals import REPO_DATA_PATH, REPO_DATA_FILE_PATH, CONFIG_FILE_PATH
from globals import repo_data
from globals import read_yaml_file, read_json_file, write_json_file

from git_functions import git_check

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime


app = FastAPI()

@app.on_event("startup")
async def startup_event():
    global repo_data

    config_data = read_yaml_file(CONFIG_FILE_PATH)
    if not config_data:
        # stop startup if no config
        print(f"STARTUP: {CONFIG_FILE_PATH} doesn't exist, aborting startup")
        return None

    if len(config_data['repos']) == 0:
        # stop startup if no repos in json
        print(f"STARTUP: no repositories found in {CONFIG_FILE_PATH}, aborting startup")
        return None

    repo_data = read_json_file(REPO_DATA_FILE_PATH)

    if not repo_data:
        print(f"STARTUP: writing empty repo data file to {REPO_DATA_FILE_PATH}")
        repo_data = {}
        write_json_file(REPO_DATA_FILE_PATH, repo_data)

    scheduler = BackgroundScheduler()

    for repo in config_data['repos']:
        scheduler.add_job(
            git_check,
            args=[
                repo['name'],
                repo['repo_url'],
                repo['branch'],
                repo['build_command'],
                repo['deploy_command'],
            ],
            trigger=IntervalTrigger(seconds=repo['interval']),
            id=f"git_check_periodic_task_{repo['name']}",
            replace_existing=True,
            max_instances=1,
            next_run_time=datetime.now()
        )

        print(f"STARTUP: scheduler task configured for {repo['name']}, interval {repo['interval']} seconds")
    
    scheduler.start()
    print("STARTUP: scheduler started")

# # Define a root endpoint
# @app.get("/")
# def read_root():
#     return {"message": "Hello, World!"}

# # Define an endpoint with path parameter
# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: str = None):
#     return {"item_id": item_id, "q": q}

# # Define a POST endpoint
# @app.post("/items/")
# def create_item(item: dict):
#     return {"received_item": item}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)