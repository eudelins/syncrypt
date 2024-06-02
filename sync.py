#!/usr/bin/env python3

import argparse
import os
from os import listdir
from os.path import isdir
import secrets
import shutil
import subprocess


BOLD_BLUE = "\033[1;34m"
BOLD_GREEN = "\033[1;33m"
BOLD_RED = "\033[1;31m"
RESET_SEQ = "\033[0m"


def log_info(*args):
    """Displays an info logging message"""
    print(f"{BOLD_BLUE}[*]{RESET_SEQ}", *args)


def log_error(*args):
    """Displays an error logging message"""
    print(f"{BOLD_RED}[-]{RESET_SEQ}", *args)


def log_success(*args):
    """Displays a success logging message"""
    print(f"{BOLD_GREEN}[+]{RESET_SEQ}", *args)


def parse_args():
    """Returns the parsed arguments from the CLI."""
    parser = argparse.ArgumentParser(
        description="Sync your obsidian notes on GitHub (encrypted) for free!"
    )
    subparsers = parser.add_subparsers(required=True)

    init_subparser = subparsers.add_parser(
        "init",
        help=(
            "Creates the 7z encryption password and prepare the git "
            "configuration to sync your notes."
        ),
    )
    init_subparser.set_defaults(exec_command=init)

    push_subparser = subparsers.add_parser(
        "pull",
        help="Pull latest changes from your remote repository.",
    )
    push_subparser.set_defaults(exec_command=pull)

    push_subparser = subparsers.add_parser(
        "push",
        help="Push current changes to your remote repository.",
    )
    push_subparser.set_defaults(exec_command=push)
    return parser.parse_args()


BACKUP_BRANCH = "backup_branch"
BACKUP_FOLDER = ".backup"
BACKUP_REMOTE_NAME = "backup_dir"
PWD_SIZE = 32
PWD_DIR = ".pwd"
PWD_FILE = f"{PWD_DIR}/7z_password"


def init():
    """
    Creates the 7z password for the project and prepares the git
    configuration.
    """
    log_info(f"Creating '{PWD_DIR}' folder and '{PWD_FILE}' file...")
    if os.path.exists(PWD_DIR):
        log_error(f"The '{PWD_DIR}' folder already exists.")
        log_error(
            "Please manually remove it if you are sure that is what you want"
            ", and run the init command again."
        )
        exit(1)
    else:
        os.makedirs(PWD_DIR)
        with open(PWD_FILE, "w") as password_file:
            password = secrets.token_hex(PWD_SIZE)
            password_file.write(password)
            log_success(f"'{PWD_DIR}' and '{PWD_FILE}' successfully created!")

    if not os.path.exists(".gitignore"):
        log_info("Creating .gitignore...")
        with open(".gitignore", "w") as gitignore_file:
            gitignore_file.write("# Projects folders\n")
            gitignore_file.write(".backup\n")
            gitignore_file.write(".pwd\n")
            gitignore_file.write("venv\n\n")
            gitignore_file.write("# Obsidian notes folders\n")
            log_success(".gitignore successfully created!")


def retrieve_password() -> str:
    """Tries to retrieve the 7z encryption password."""
    log_info("Trying to retrieve encryption password...")
    if not os.path.exists(PWD_FILE):
        log_error(f"'{PWD_FILE}' could not been found!\n")
        log_error(
            "Please run `python3 sync.py init` first, or import your existing"
            " 7z password in this file."
        )
        exit(2)
    with open(PWD_FILE, "r") as password_file:
        password = password_file.read()
        log_success("Password successfully retrieved!")
        return password


def run_command(command: str, ignore_error: bool = False) -> int:
    """Executes and logs a shell command."""
    log_info(command)
    rc = os.system(command)
    if rc != 0:
        if ignore_error:
            log_error(f"{command} failed.")
        else:
            log_error(f"{command} failed. Aborting.")
            exit(rc)
    else:
        log_success("Success!")
    return rc


def pull():
    """Pulls the latest encrypted notes from GitHub, and decrypts them."""
    backup_notes()

    log_info("Pulling latest changes...")
    for dir in filter(contains_git_dir, get_obsidian_folders()):
        shutil.rmtree(dir)
    run_command("git pull")

    password = retrieve_password()
    encrypted_archives = filter(lambda file: file.endswith(".7z"), listdir())
    for enc_archive in encrypted_archives:
        log_info(f"Decrypting {enc_archive}...")
        run_command(f"7z x -y -p{password} {enc_archive}")

        log_info("Restoring notes...")
        uncompressed_archive = enc_archive.removesuffix(".7z")
        run_command(f"cd {uncompressed_archive} && git restore .")

    log_info("Merging with backup notes...")
    for dir in filter(contains_git_dir, get_obsidian_folders()):
        backup_dir = f"{BACKUP_FOLDER}/{dir}"
        if contains_git_dir(backup_dir):
            run_command(
                f"cd {dir} && "
                f"git remote add {BACKUP_REMOTE_NAME} ../{backup_dir}",
                ignore_error=True,
            )
            run_command(
                f"cd {dir} && git fetch {BACKUP_REMOTE_NAME}",
                ignore_error=True,
            )
            rc = run_command(
                f"cd {dir} && git merge {BACKUP_REMOTE_NAME}/{BACKUP_BRANCH}",
                ignore_error=True,
            )
            if rc != 0:
                log_error(
                    "Merge failed. Carefully check the logs and resolve your "
                    "conflicts."
                )


def push():
    """Encrypts the notes and push them on GitHub."""
    backup_notes()
    password = retrieve_password()
    for dir in get_obsidian_folders():
        if ".git" not in listdir(dir):
            add_to_gitignore(dir)
            run_command(f"cd {dir} && git init")
            run_command(f"cd {dir} && git branch -M main")

        run_command(f"cd {dir} && git add .")
        commit_cmd = commit_command("Sync")
        run_command(f"cd {dir} && {commit_cmd}")
        remote_list = subprocess.getoutput(f"cd {dir} && git remote show")
        if BACKUP_REMOTE_NAME in remote_list.split("\n"):
            run_command(f"cd {dir} && git remote remove {BACKUP_REMOTE_NAME}")

        branch_list = subprocess.getoutput(f"cd {dir} && git branch")
        if f"* {BACKUP_BRANCH}" in branch_list.split("\n"):
            run_command(f"cd {dir} && git branch -D {BACKUP_BRANCH}")

        log_info(f"Encrypting {dir}...")
        run_command(f"7z a -p{password} {dir}.7z {dir}/.git")

    run_command("git add .")
    run_command(commit_command("Sync"))
    run_command("git push -u origin main")


def add_to_gitignore(dir: str):
    """Add the directory to the .gitignore"""
    with open(".gitignore", "a+") as gitignore_file:
        if dir not in gitignore_file.readlines():
            gitignore_file.write(f"{dir}\n")


def backup_notes():
    """Creates backup of the obsidian notes"""
    log_info("Creating existing notes backup...")
    if os.path.exists(BACKUP_FOLDER):
        shutil.rmtree(BACKUP_FOLDER)

    os.makedirs(BACKUP_FOLDER)
    for dir in get_obsidian_folders():
        backup_dir = f"{BACKUP_FOLDER}/{dir}"
        shutil.copytree(dir, backup_dir)
        if ".git" in listdir(dir):
            run_command(f"cd {backup_dir} && git checkout -B {BACKUP_BRANCH}")
            run_command(f"cd {backup_dir} && git add .")
            commit_cmd = commit_command("Backup")
            run_command(
                f"cd {backup_dir} && {commit_cmd}",
                ignore_error=True,
            )
        log_success("Notes successfully backed up!")


def get_obsidian_folders():
    """Retrieves the obsidian vaults' name in the current directories"""
    return filter(is_obsidian_vault, listdir())


def is_obsidian_vault(dir: str):
    """
    Returns True if the provided path points to an Obsidian vaults, False
    otherwise.
    """
    return isdir(dir) and dir != ".git" and ".obsidian" in listdir(dir)


def contains_git_dir(dir: str):
    """
    Returns True if the directory contain a .git folder, False otherwise.
    """
    return isdir(dir) and ".git" in listdir(dir)


def commit_command(msg: str) -> str:
    """Returns the git commit command with th provided message."""
    return f"git diff-index --quiet HEAD || git commit -m '{msg}'"


def main():
    args = parse_args()
    args.exec_command()


if __name__ == "__main__":
    main()
