import os
import sys
import json
import hashlib
import shutil
import difflib
from datetime import datetime

MINIGIT_DIR = ".minigit"
COMMITS_DIR = os.path.join(MINIGIT_DIR, "commits")
INDEX_FILE = os.path.join(MINIGIT_DIR, "index.json")
PRS_FILE = os.path.join(MINIGIT_DIR, "prs.json")
BRANCHES_DIR = os.path.join(MINIGIT_DIR, "branches")


def ensure_repo():
    if not os.path.exists(MINIGIT_DIR):
        print("Not a MiniGit repo. Run `init` first.")
        sys.exit(1)


def load_index():
    with open(INDEX_FILE, "r") as f:
        return json.load(f)


def save_index(index):
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def init():
    if os.path.exists(MINIGIT_DIR):
        print("Repo already initialized.")
        return

    os.makedirs(COMMITS_DIR)
    os.makedirs(BRANCHES_DIR)
    with open(INDEX_FILE, "w") as f:
        json.dump({"staged": [], "branches": {"main": []}, "current_branch": "main"}, f)
    with open(PRS_FILE, "w") as f:
        json.dump([], f)

    print("Initialized empty MiniGit repo.")


def add(filename):
    ensure_repo()
    if not os.path.exists(filename):
        print(f"File '{filename}' not found.")
        return

    index = load_index()
    if filename not in index["staged"]:
        index["staged"].append(filename)
    save_index(index)
    print(f"Added '{filename}' to staging.")


def commit(message):
    ensure_repo()
    index = load_index()
    branch = index["current_branch"]
    commits = index["branches"].get(branch, [])
    last_commit = commits[-1] if commits else None
    last_commit_files = set(last_commit["files"]) if last_commit else set()

    # Auto-stage modified and new files
    staged = index["staged"]
    for file in os.listdir("."):
        if file == MINIGIT_DIR or file.startswith("."):
            continue
        if os.path.isfile(file):
            if file in last_commit_files:
                # Check if modified
                last_commit_path = os.path.join(COMMITS_DIR, last_commit["id"], file) if last_commit else None
                if last_commit_path and os.path.exists(last_commit_path):
                    with open(file, "rb") as f1, open(last_commit_path, "rb") as f2:
                        if hashlib.sha1(f1.read()).hexdigest() != hashlib.sha1(f2.read()).hexdigest():
                            if file not in staged:
                                staged.append(file)
                                print(f"Auto-staged modified file '{file}'")
            else:
                # New file not in last commit
                if file not in staged:
                    staged.append(file)
                    print(f"Auto-staged new file '{file}'")
    
    if not staged:
        print("No changes to commit")
        return
    
    index["staged"] = staged
    save_index(index)

    commit_id = hashlib.sha1((message + str(datetime.now())).encode()).hexdigest()[:7]
    commit_path = os.path.join(COMMITS_DIR, commit_id)
    os.makedirs(commit_path)

    for file in staged:
        shutil.copy(file, os.path.join(commit_path, file))

    commit_data = {
        "id": commit_id,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "files": staged.copy()
    }

    index["branches"][branch].append(commit_data)
    index["staged"] = []
    save_index(index)

    print(f"Committed to {branch} as {commit_id}: {message}")


def log():
    ensure_repo()
    index = load_index()
    branch = index["current_branch"]
    commits = index["branches"].get(branch, [])
    for commit in reversed(commits):
        print(f"Commit {commit['id']}")
        print(f"Date: {commit['timestamp']}")
        print(f"\n    {commit['message']}\n")


def branch(branch_name):
    ensure_repo()
    index = load_index()
    if branch_name in index["branches"]:
        print("Branch already exists.")
        return

    current = index["current_branch"]
    index["branches"][branch_name] = index["branches"][current].copy()
    save_index(index)
    print(f"Created branch '{branch_name}'.")


def checkout(branch_name):
    ensure_repo()
    index = load_index()
    if branch_name not in index["branches"]:
        print("No such branch.")
        return
    
    # Save current branch before switching
    previous_branch = index["current_branch"]
    
    # Update current branch in index
    index["current_branch"] = branch_name
    save_index(index)
    
    # Get the latest commit from the target branch
    branch_commits = index["branches"][branch_name]
    if branch_commits:  # Only restore files if the branch has commits
        latest_commit = branch_commits[-1]
        commit_id = latest_commit["id"]
        commit_path = os.path.join(COMMITS_DIR, commit_id)
        
        # Restore files from the commit to the working directory
        for file in latest_commit["files"]:
            source_file = os.path.join(commit_path, file)
            if os.path.exists(source_file):
                shutil.copy(source_file, file)
                print(f"Restored '{file}' from commit {commit_id}")
    
    print(f"Switched to branch '{branch_name}'.")


def create_pr(source, target):
    ensure_repo()
    index = load_index()
    if source not in index["branches"] or target not in index["branches"]:
        print("One of the branches doesn't exist.")
        return

    with open(PRS_FILE, "r") as f:
        prs = json.load(f)

    pr_id = len(prs) + 1
    prs.append({
        "id": pr_id,
        "source": source,
        "target": target,
        "status": "open"
    })

    with open(PRS_FILE, "w") as f:
        json.dump(prs, f, indent=2)

    print(f"Pull request #{pr_id} created from {source} → {target}.")


def pr_list():
    ensure_repo()
    with open(PRS_FILE, "r") as f:
        prs = json.load(f)

    if not prs:
        print("No pull requests.")
        return

    for pr in prs:
        print(f"PR #{pr['id']} | {pr['source']} → {pr['target']} | Status: {pr['status']}")


def pr_merge(pr_id):
    ensure_repo()
    pr_id = int(pr_id)
    with open(PRS_FILE, "r") as f:
        prs = json.load(f)

    for pr in prs:
        if pr["id"] == pr_id and pr["status"] == "open":
            source = pr["source"]
            target = pr["target"]

            index = load_index()
            src_commits = index["branches"][source]
            tgt_commits = index["branches"][target]

            # Find commits in source not in target
            tgt_commit_ids = {c["id"] for c in tgt_commits}
            new_commits = [c for c in src_commits if c["id"] not in tgt_commit_ids]
            index["branches"][target].extend(new_commits)
            save_index(index)

            pr["status"] = "merged"
            with open(PRS_FILE, "w") as f:
                json.dump(prs, f, indent=2)

            print(f"PR #{pr_id} merged successfully.")
            return

    print(f"PR #{pr_id} not found or already merged.")


def branch_list():
    ensure_repo()
    index = load_index()
    current = index["current_branch"]
    branches = index["branches"].keys()
    
    if not branches:
        print("No branches found.")
        return
    
    for branch in branches:
        if branch == current:
            print(f"* {branch} (current)")
        else:
            print(f"  {branch}")


def delete_branch(branch_name):
    ensure_repo()
    index = load_index()
    current = index["current_branch"]
    
    if branch_name not in index["branches"]:
        print(f"Branch '{branch_name}' not found.")
        return
    
    if branch_name == current:
        print(f"Cannot delete the current branch '{branch_name}'.")
        return
    
    if branch_name == "main":
        print("Cannot delete the 'main' branch.")
        return
    
    del index["branches"][branch_name]
    save_index(index)
    print(f"Deleted branch '{branch_name}'.")


def status():
    ensure_repo()
    index = load_index()
    branch = index["current_branch"]
    print(f"On branch {branch}")
    
    commits = index["branches"].get(branch, [])
    if commits:
        last_commit = commits[-1]
        print(f"Last commit: {last_commit['id']} - {last_commit['message']}")
    else:
        print("No commits yet")
    
    staged = index["staged"]
    if staged:
        print("\nStaged files:")
        for file in staged:
            print(f"  - {file}")
    else:
        print("\nNo staged files")
    
    # Check for modified or new files not yet staged
    modified_files = []
    new_files = []
    last_commit_files = set(last_commit["files"]) if commits else set()
    for file in os.listdir("."):
        if file == MINIGIT_DIR or file.startswith("."):
            continue
        if os.path.isfile(file):
            if file in last_commit_files:
                # Check if modified
                last_commit_path = os.path.join(COMMITS_DIR, last_commit["id"], file) if commits else None
                if last_commit_path and os.path.exists(last_commit_path):
                    with open(file, "rb") as f1, open(last_commit_path, "rb") as f2:
                        if hashlib.sha1(f1.read()).hexdigest() != hashlib.sha1(f2.read()).hexdigest():
                            if file not in staged:
                                modified_files.append(file)
            else:
                # New file not in last commit
                if file not in staged:
                    new_files.append(file)
    
    if modified_files:
        print("\nModified files not staged:")
        for file in modified_files:
            print(f"  - {file}")
    if new_files:
        print("\nNew files not staged (will be auto-staged on commit):")
        for file in new_files:
            print(f"  - {file}")
    if not modified_files and not new_files:
        print("\nNo modified or new files")


def diff_commits(commit1_id, commit2_id):
    ensure_repo()
    commit1_path = os.path.join(COMMITS_DIR, commit1_id)
    commit2_path = os.path.join(COMMITS_DIR, commit2_id)
    
    if not os.path.exists(commit1_path):
        print(f"Commit {commit1_id} not found.")
        return
    if not os.path.exists(commit2_path):
        print(f"Commit {commit2_id} not found.")
        return
    
    index = load_index()
    commit1_data = next((c for branch in index["branches"].values() for c in branch if c["id"] == commit1_id), None)
    commit2_data = next((c for branch in index["branches"].values() for c in branch if c["id"] == commit2_id), None)
    
    if not commit1_data or not commit2_data:
        print("Commit data not found in index.")
        return
    
    print(f"Diff between commit {commit1_id} and {commit2_id}")
    _compare_files(commit1_data["files"], commit1_path, commit2_data["files"], commit2_path)


def diff_branches(branch1_name, branch2_name):
    ensure_repo()
    index = load_index()
    
    if branch1_name not in index["branches"]:
        print(f"Branch '{branch1_name}' not found.")
        return
    if branch2_name not in index["branches"]:
        print(f"Branch '{branch2_name}' not found.")
        return
    
    branch1_commits = index["branches"][branch1_name]
    branch2_commits = index["branches"][branch2_name]
    
    if not branch1_commits or not branch2_commits:
        print("One or both branches have no commits.")
        return
    
    commit1_id = branch1_commits[-1]["id"]
    commit2_id = branch2_commits[-1]["id"]
    commit1_path = os.path.join(COMMITS_DIR, commit1_id)
    commit2_path = os.path.join(COMMITS_DIR, commit2_id)
    
    print(f"Diff between branch '{branch1_name}' (commit {commit1_id}) and '{branch2_name}' (commit {commit2_id})")
    _compare_files(branch1_commits[-1]["files"], commit1_path, branch2_commits[-1]["files"], commit2_path)


def diff_pr(pr_id):
    ensure_repo()
    try:
        pr_id = int(pr_id)
    except ValueError:
        print("Error: PR ID must be a number. Use 'python minigit.py pr-list' to see available PRs.")
        return
    
    with open(PRS_FILE, "r") as f:
        prs = json.load(f)
    
    pr = next((p for p in prs if p["id"] == pr_id), None)
    if not pr:
        print(f"Pull request #{pr_id} not found.")
        return
    
    source = pr["source"]
    target = pr["target"]
    index = load_index()
    
    if source not in index["branches"] or target not in index["branches"]:
        print("One of the branches in the PR no longer exists.")
        return
    
    source_commits = index["branches"][source]
    target_commits = index["branches"][target]
    
    if not source_commits or not target_commits:
        print("One or both branches have no commits.")
        return
    
    source_commit_id = source_commits[-1]["id"]
    target_commit_id = target_commits[-1]["id"]
    source_path = os.path.join(COMMITS_DIR, source_commit_id)
    target_path = os.path.join(COMMITS_DIR, target_commit_id)
    
    print(f"Diff for PR #{pr_id}: {source} (commit {source_commit_id}) -> {target} (commit {target_commit_id})")
    _compare_files(source_commits[-1]["files"], source_path, target_commits[-1]["files"], target_path)


def revert(commit_id):
    ensure_repo()
    index = load_index()
    branch = index["current_branch"]
    commits = index["branches"].get(branch, [])
    
    commit_to_revert = next((c for c in commits if c["id"] == commit_id), None)
    if not commit_to_revert:
        print(f"Commit {commit_id} not found in current branch '{branch}'.")
        return
    
    # Create a new commit that undoes the changes of the specified commit
    # For simplicity, we'll restore the files to the state before this commit
    commit_index = commits.index(commit_to_revert)
    if commit_index == 0:
        print("Cannot revert the first commit. Use reset if you want to remove all history.")
        return
    
    previous_commit = commits[commit_index - 1]
    previous_commit_path = os.path.join(COMMITS_DIR, previous_commit["id"])
    new_commit_id = hashlib.sha1((f"Revert of {commit_id}" + str(datetime.now())).encode()).hexdigest()[:7]
    new_commit_path = os.path.join(COMMITS_DIR, new_commit_id)
    os.makedirs(new_commit_path)
    
    # Copy files from the previous commit to the new commit
    for file in previous_commit["files"]:
        source_file = os.path.join(previous_commit_path, file)
        if os.path.exists(source_file):
            shutil.copy(source_file, os.path.join(new_commit_path, file))
            shutil.copy(source_file, file)  # Also update working directory
    
    new_commit_data = {
        "id": new_commit_id,
        "message": f"Revert commit {commit_id}",
        "timestamp": datetime.now().isoformat(),
        "files": previous_commit["files"].copy()
    }
    
    index["branches"][branch].append(new_commit_data)
    index["staged"] = []
    save_index(index)
    
    print(f"Created revert commit {new_commit_id} to undo changes from {commit_id}")


def reset(commit_id):
    ensure_repo()
    index = load_index()
    branch = index["current_branch"]
    commits = index["branches"].get(branch, [])
    
    commit_to_reset_to = next((c for c in commits if c["id"] == commit_id), None)
    if not commit_to_reset_to:
        print(f"Commit {commit_id} not found in current branch '{branch}'.")
        return
    
    commit_index = commits.index(commit_to_reset_to)
    if commit_index == len(commits) - 1:
        print("Already at this commit. No reset needed.")
        return
    
    # Truncate history after the specified commit
    index["branches"][branch] = commits[:commit_index + 1]
    index["staged"] = []
    save_index(index)
    
    # Restore files to the state of the reset commit
    reset_commit_path = os.path.join(COMMITS_DIR, commit_id)
    for file in commit_to_reset_to["files"]:
        source_file = os.path.join(reset_commit_path, file)
        if os.path.exists(source_file):
            shutil.copy(source_file, file)
            print(f"Restored '{file}' to state in commit {commit_id}")
    
    print(f"Reset branch '{branch}' to commit {commit_id}. Subsequent history discarded.")


def _compare_files(files1, path1, files2, path2):
    all_files = set(files1 + files2)
    for file in all_files:
        file1_path = os.path.join(path1, file)
        file2_path = os.path.join(path2, file)
        
        if file not in files1:
            print(f"\nFile '{file}' was added in the second commit/branch.")
            with open(file2_path, "r") as f:
                content = f.readlines()
            print("".join(["+ " + line for line in content[:5]]))
            if len(content) > 5:
                print(f"... and {len(content) - 5} more lines")
        elif file not in files2:
            print(f"\nFile '{file}' was removed in the second commit/branch.")
            with open(file1_path, "r") as f:
                content = f.readlines()
            print("".join(["- " + line for line in content[:5]]))
            if len(content) > 5:
                print(f"... and {len(content) - 5} more lines")
        else:
            with open(file1_path, "r") as f1, open(file2_path, "r") as f2:
                content1 = f1.readlines()
                content2 = f2.readlines()
            if content1 != content2:
                print(f"\nChanges in '{file}':")
                diff = difflib.unified_diff(content1, content2, fromfile=f"a/{file}", tofile=f"b/{file}", n=3)
                for line in list(diff)[:10]:  # Limit to first 10 lines of diff for brevity
                    print(line, end="")
                if len(list(difflib.unified_diff(content1, content2))) > 10:
                    print("... (diff truncated)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python minigit.py <command> [args]")
        return

    cmd = sys.argv[1].lower()

    match cmd:
        case "init":
            init()
        case "add":
            if len(sys.argv) < 3:
                print("Usage: python minigit.py add <filename>")
                return
            add(sys.argv[2])
        case "commit":
            if len(sys.argv) < 3:
                print("Usage: python minigit.py commit <message>")
                return
            commit(sys.argv[2])
        case "log":
            log()
        case "branch":
            if len(sys.argv) < 3:
                print("Usage: python minigit.py branch <branch_name>")
                return
            branch(sys.argv[2])
        case "checkout":
            if len(sys.argv) < 3:
                print("Usage: python minigit.py checkout <branch_name>")
                return
            checkout(sys.argv[2])
        case "create-pr":
            if len(sys.argv) < 4:
                print("Usage: python minigit.py create-pr <source_branch> <target_branch>")
                return
            create_pr(sys.argv[2], sys.argv[3])
        case "pr-list":
            pr_list()
        case "pr-merge":
            if len(sys.argv) < 3:
                print("Usage: python minigit.py pr-merge <pr_id>")
                return
            try:
                pr_id = int(sys.argv[2])
                pr_merge(sys.argv[2])
            except ValueError:
                print("Error: PR ID must be a number. Use 'python minigit.py pr-list' to see available PRs.")
                return
        case "status":
            status()
        case "list":
            branch_list()
        case "delete":
            if len(sys.argv) < 3:
                print("Usage: python minigit.py delete <branch_name>")
                return
            delete_branch(sys.argv[2])
        case "diff":
            if len(sys.argv) < 4:
                print("Usage: python minigit.py diff <commit1_id> <commit2_id>")
                return
            diff_commits(sys.argv[2], sys.argv[3])
        case "diff-branch":
            if len(sys.argv) < 4:
                print("Usage: python minigit.py diff-branch <branch1_name> <branch2_name>")
                return
            diff_branches(sys.argv[2], sys.argv[3])
        case "pr-diff":
            if len(sys.argv) < 3:
                print("Usage: python minigit.py pr-diff <pr_id>")
                return
            diff_pr(sys.argv[2])
        case "revert":
            if len(sys.argv) < 3:
                print("Usage: python minigit.py revert <commit_id>")
                return
            revert(sys.argv[2])
        case "reset":
            if len(sys.argv) < 3:
                print("Usage: python minigit.py reset <commit_id>")
                return
            reset(sys.argv[2])
        case _:
            print("Unknown command.")


if __name__ == "__main__":
    main()
