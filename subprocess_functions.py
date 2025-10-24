import os, subprocess


def get_remote_hash(repo_url, branch='main'):
    result = subprocess.check_output(
        ["git", "ls-remote", repo_url, f"refs/heads/{branch}"],
        text=True
    )
    return result.split()[0] if result else None

def clone_repo(repo_url, repo_dir, branch="main"):
    if not os.path.exists(os.path.join(repo_dir, ".git")):
        subprocess.run(
            ["git", "clone", "--branch", branch, "--single-branch", repo_url, repo_dir],
            check=True
        )
    else:
        print("Repository already exists.")

def pull_repo(repo_dir):
    subprocess.run(
        ["git", "-C", repo_dir, "pull", "--rebase"],
        check=True
    )

def run_command(cmd, cwd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise Exception(f"Command failed: {cmd}")
    print(result.stdout)