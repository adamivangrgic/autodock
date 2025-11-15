import os, subprocess
import asyncio

def run_command(cmd, cwd='/'):
    print(f"SUBPROCESS: Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, text=True)
    if result.returncode != 0:
        raise Exception(f"SUBPROCESS: {cmd} failed: {result.stderr}")

def check_output(cmd, cwd='/'):
    print(f"SUBPROCESS: Checking output from: {cmd}")
    result = subprocess.check_output(cmd, shell=True, cwd=cwd, text=True, timeout=60)
    
    return result if result else None

async def poll_output(cmd, cwd='/', callback=None):
    print(f"SUBPROCESS: Polling output from: {cmd}")
    
    async def read_output(proc, cb):
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            line = line.decode().strip()
            if cb:
                cb(line)
        
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd
    )
    
    read_task = asyncio.create_task(read_output(process, callback))
    
    try:
        await process.wait()
    finally:
        await read_task