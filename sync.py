#!/usr/bin/env python3

import argparse
import os
from os import listdir
from os.path import isdir
import secrets
import shutil
import subprocess


BOLD_BLUE = "\033[1;34m"
BOLD_RED = "\033[1;31m"
RESET_SEQ = "\033[0m"


def log_info(*args):
    """Displays an info logging message"""
    print(f"{BOLD_BLUE}[*]{RESET_SEQ}", *args)


def log_error(*args):
    """Displays an error logging message"""
    print(f"{BOLD_RED}[-]{RESET_SEQ}", *args)

# TODO: Add log_success (use it after init, sync success)


def parse_args():
    """Returns the parsed arguments from the CLI."""
    parser = argparse.ArgumentParser(
        description="Sync your obsidian notes on GitHub (encrypted) for free!"
    )
    subparsers = parser.add_subparsers(required=True)

    init_subparser = subparsers.add_parser(
        "init",
        help="Creates the 7z encryption password and prepare the git configuration to sync your notes.",
    )
    init_subparser.set_defaults(exec_command=init)

    sync_subparser = subparsers.add_parser(
        "sync",
        help="Sync doc.",
    )
    sync_subparser.set_defaults(exec_command=sync)
    return parser.parse_args()


BACKUP_FOLDER = ".backup"
PWD_SIZE = 32
PWD_DIR = ".pwd"
PWD_FILE = f"{PWD_DIR}/7z_password"


def init():
    """Creates the 7z password for the project and prepares the git configuration"""
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
        log_info(f"'{PWD_DIR}' folder successfully created!")
        with open(PWD_FILE, "w") as password_file:
            password = secrets.token_hex(PWD_SIZE)
            password_file.write(password)
            log_info(f"'{PWD_FILE}' successfully created!")
            # TODO: git init in each directory


def retrieve_password():
    """Tries to retrieve the 7z encryption password"""
    if not os.path.exists(PWD_FILE):
        log_error(f"'{PWD_FILE}' could not been found!\n")
        log_error(
            "Please run `python3 sync.py init` first, or import your existing"
            " 7z password in this file."
        )
        exit(2)
    with open(PWD_FILE, "r") as password_file:
        return password_file.read()


def sync():
    log_info("Fetching the remote repository changes...")
    log_info("git fetch")
    os.system("git fetch")
    log_info("Checking if changes have been added...")
    log_info("git diff --name-only origin/main")
    subprocess.getoutput()
    return 0

    # # Pull operation
    # Stash/commit current state?
    # backup_notes() 
    # git pull
    # for each encrypted_file
        # 7z x -p{pwd} encrypted_file
        # git remote add backup_dir ../.backup/encrypted_file_name 
        # git pull backup_dir main:backup_branch

    # log_info("7z encryption password successfully retrieved")

    # if git status
    # # Push operation
    # backup_notes()
    # retrieve pwd
    # for each notes_folder
        # cd notes_folder && git commit -m "Sync" && cd -
        # files_and_dirs = ls -a notes_folder
        # rm -r notes_folder/files_and_dirs
        # 7z a -p{pwd} notes_folder_git.7z notes_folder/.git
    # git push


def backup_notes():
    """Creates backup of the obsidian notes"""
    if os.path.exists(BACKUP_FOLDER):
        shutil.rmtree(BACKUP_FOLDER)

    os.makedirs(BACKUP_FOLDER)
    for dir in get_obsidian_folder():
        shutil.copytree(
            dir,
            f"{BACKUP_FOLDER}/{dir}",
            ignore=shutil.ignore_patterns(f".git")
        )


def get_obsidian_folder():
    """Retrieves the obsidian vaults' name in the current directories"""
    return filter(
        lambda dir: isdir(dir) and dir != ".git" and ".obsidian" in listdir(dir),
        listdir(),
    )


def main():
    args = parse_args()
    args.exec_command()


if __name__ == "__main__":
    backup_notes()
    # main()
