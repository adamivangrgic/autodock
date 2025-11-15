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
        lines_processed = 0
        while True:
            line = await process.stdout.readline()
            if not line:  # EOF
                break
                
            line = line.decode().strip()
            if callback:
                callback(line)
            else:
                print(line)
            
            lines_processed += 1
            # Yield control every 5 lines to prevent blocking
            if lines_processed % 5 == 0:
                await asyncio.sleep(0)
                
    except Exception as e:
        print(f"Error reading output: {e}")
    finally:
        await process.wait()