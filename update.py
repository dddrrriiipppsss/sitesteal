import git
import os

def update_repo():
    repo_url = "https://github.com/dddrrriiipppsss/sitesteal.git"
    local_repo_path = os.getcwd()

    try:
        repo = git.Repo(local_repo_path)
        origin = repo.remotes.origin
        origin.pull()
        print("Repository updated successfully.")
    except Exception as e:
        print(f"Failed to update repository: {e}")

if __name__ == "__main__":
    update_repo()
