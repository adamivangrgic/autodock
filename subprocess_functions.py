import os, subprocess, time, asyncio

def run_command(cmd, cwd='/'):
    print(f"SUBPROCESS: Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, text=True)
    if result.returncode != 0:
        print(f"SUBPROCESS: Error: {result.stderr}")
        raise Exception(f"SUBPROCESS: Command failed: {cmd}")

def check_output(cmd, cwd='/'):
    print(f"SUBPROCESS: Checking output from: {cmd}")
    result = subprocess.check_output(cmd, shell=True, cwd=cwd, text=True, timeout=60)
    
    return result if result else None

async def poll_output(cmd, cwd='/', callback=None):
    print(f"SUBPROCESS: Polling output from: {cmd}")
    def execute_with_callback():
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=cwd, text=True, bufsize=1)
        
        try:
            while True:
                if process.poll() is not None:
                    break
                    
                output = process.stdout.readline()
                if output and callback:
                    callback(output.strip())
                elif output:
                    print(output.strip())
                else:
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            process.terminate()
        
        remaining_output, _ = process.communicate()
        if remaining_output and callback:
            callback(remaining_output.strip())
        elif remaining_output:
            print(remaining_output.strip())

    await asyncio.to_thread(execute_with_callback)