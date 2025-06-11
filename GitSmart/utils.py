import os
import subprocess

def get_git_root() -> str:
    """
    Returns the absolute path to the root of the current git repository.
    Raises RuntimeError if not in a git repo.
    """
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            universal_newlines=True
        ).strip()
        return root
    except subprocess.CalledProcessError:
        raise RuntimeError("Not inside a git repository.")

def chdir_to_git_root():
    os.chdir(get_git_root())
