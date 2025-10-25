import os, subprocess


def get_remote_hash(repo_url, branch='main'):
    print(f"    SUBPROCESS: Getting {repo_url} {branch} hash")
    result = subprocess.check_output(
        ["git", "ls-remote", repo_url, f"refs/heads/{branch}"],
        text=True
    )
    return result.split()[0] if result else None

def clone_repo(repo_url, repo_dir, branch="main"):
    print(f"    SUBPROCESS: Cloning into repo {repo_url} {branch}")
    if not os.path.exists(os.path.join(repo_dir, ".git")):
        subprocess.run(
            ["git", "clone", "--branch", branch, "--single-branch", repo_url, repo_dir],
            check=True, 
            timeout=600
        )
        print("    SUBPROCESS: Repo successfully cloned.")
    else:
        print("    SUBPROCESS: Repository already exists.")

def pull_repo(repo_dir):
    print(f"    SUBPROCESS: Pulling repo {repo_dir}")
    subprocess.run(
        ["git", "pull", "--rebase"],
        check=True,
        cwd=repo_dir
    )
    print("    SUBPROCESS: Repo successfully pulled.")

def run_command(cmd, cwd):
    print(f"    SUBPROCESS: Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, check=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"    SUBPROCESS: Error: {result.stderr}")
        raise Exception(f"    SUBPROCESS: Command failed: {cmd}")
    #print(f"    SUBPROCESS: {result.stdout}")