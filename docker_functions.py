import json
import asyncio

from subprocess_functions import run_command, check_output, poll_output


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