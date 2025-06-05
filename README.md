# MiniGit

A simplified version of Git implemented in Python for educational purposes and basic version control.

## Overview

MiniGit is a lightweight version control system that mimics basic functionality of Git. It allows you to initialize a repository, add files, commit changes, view logs, checkout previous commits, create branches, merge branches, and even handle simple pull requests.

## Getting Started

### Prerequisites
- Python 3.x installed on your system

### Installation
1. Clone or download this repository to your local machine.
2. Navigate to the project directory.

### Usage

Run the MiniGit commands using the Python script `minigit.py`. Below are the primary commands:

- **Initialize a repository**: `python minigit.py init`
- **Add files to staging**: `python minigit.py add <file1> <file2> ...`
- **Commit changes**: `python minigit.py commit -m "Your commit message"`
- **View commit log**: `python minigit.py log`
- **Checkout a commit/branch**: `python minigit.py checkout <commit_id or branch_name>`
- **Create a branch**: `python minigit.py branch <branch_name>`
- **Merge a branch**: `python minigit.py merge <branch_name>`
- **Create a pull request**: `python minigit.py pr create <source_branch> <target_branch>`
- **List pull requests**: `python minigit.py pr list`
- **Merge a pull request**: `python minigit.py pr merge <pr_id>`

## Project Structure

- `.minigit/` - Hidden directory storing all repository data like commits, branches, and pull requests.
- `minigit.py` - Main script to run MiniGit commands.

## Contributing

Feel free to fork this project, make improvements, and submit pull requests. Any contributions to enhance MiniGit are welcome!

## License

This project is open source and available under the MIT License.
