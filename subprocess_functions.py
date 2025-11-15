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
    
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd
    )
    
    try:
        while True:
            try:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=0.1)
            except asyncio.TimeoutError:
                if process.returncode is not None:
                    break
                continue
                
            if not line:
                break
                
            line = line.decode().strip()
            if callback:
                callback(line)
                
    except Exception as e:
        print(f"Error reading output: {e}")
    finally:
        await process.wait()