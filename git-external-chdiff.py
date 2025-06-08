#!/usr/bin/env python
# encoding: utf-8
"""
git-external-chdiff

Created by Dan Weeks (dan [AT] danimal [DOT] org) on 2008-02-27.
Released to the Public Domain.
Refatorado em 2025 por Gabriel Izidoro, João Victor.
"""

import sys
import subprocess
import os

def parse_external_diff_args(argv):
    """
    Extracts the paths of the old and new files from the arguments
    automatically passed by Git (via GIT_EXTERNAL_DIFF).

    Git sends the following arguments:
    argv[0] - script
    argv[1] - repository path
    argv[2] - original file (in old revision)
    argv[3] - old SHA number
    argv[4] - repository path
    argv[5] - modified file (in current state)
    argv[6] - new SHA number
    """
    try:
        old_file = argv[2]
        new_file = argv[5]
        return old_file, new_file
    except IndexError:
        print("Error: Insufficient arguments provided by Git.", file=sys.stderr)
        sys.exit(1)

def run_chdiff(old_file, new_file, wait=True, verbose=False):
    """
    Executa o utilitário chdiff para comparar dois arquivos.
    """
    wait_flag = '--wait' if wait else ''
    command = ['chdiff', wait_flag, old_file, new_file]

    if verbose:
        print(f'Running: {" ".join(command)}')

    try:
        subprocess.run(command, env=os.environ)
    except FileNotFoundError:
        print("Error: 'chdiff' not found on the system.", file=sys.stderr)
        sys.exit(1)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    old_file, new_file = parse_external_diff_args(argv)
    run_chdiff(old_file, new_file, wait=True, verbose=False)

if __name__ == '__main__':
    main()