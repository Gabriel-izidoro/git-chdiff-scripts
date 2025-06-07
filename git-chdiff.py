#!/usr/bin/env python
# encoding: utf-8
"""
git-chdiff

Created by Dan Weeks (dan [AT] danimal [DOT] org) on 2008-02-20.
Released to the Public Domain.
"""

import getopt
import os
import subprocess
import sys
import tempfile

import pwd
import getpass

HELP_MESSAGE = '''
git-chdiff <opts> [file1, file2, ...]

display diffs of git files using the chdiff utility 

  -h, --help        display this message
  -r, --revision    the revision of the file to use 
                       defaults to 'HEAD~1', the previous commit
  -w, --wait        cause chdiff to wait between files
  -v, --verbose     print more messages during operation
  --clean           clean any temp files that might have been left around
'''

TEMP_FILE_SUFFIX = '.temp'
TEMP_FILE_PREFIX = 'git-chdiff'
TEMP_DIRECTORY = '/var/tmp'

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def clean_temp_files(verbose=False):
    """
    because we don't always wait for chdiff we can't always clean up
    the temp files we make.  This will wipe out all git-chdiff temp
    files owned by us.
    """

    try:
        if verbose:
            print('scanning for git-chdiff temp files to clean')
        my_uid = pwd.getpwnam(getpass.getuser())[2]
        files_in_tmp = os.listdir(TEMP_DIRECTORY)
        for file_name in files_in_tmp:
            normalized_file = os.path.join(TEMP_DIRECTORY, file_name)
            # skip directories
            if not os.path.isfile(normalized_file):
                continue
            # skip anything not named right
            if not file_name.startswith(TEMP_FILE_PREFIX):
                continue
            # skip if it's not our file
            if os.stat(normalized_file)[4] != my_uid:
                continue
            # if we're here we own the file and it's named correctly
            # remove it
            if verbose:
                print('removing temp file: %s' % normalized_file)
            os.unlink(normalized_file)
        return 0
    except Exception as e:
        if verbose:
            print('Clean failed:', e, file=sys.stderr)
        return 1

def main(argv=None):
    """
    the basic work location
    """
    
    # set up the defaults
    should_clean = False
    revision = 'HEAD~0' # get the previous commit
    wait = False
    verbose = False
    
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], 'hr:wv', ['clean',
                                                          'help', 
                                                          'revision=',
                                                          'wait',
                                                          'verbose'])
        except getopt.error as msg:
            raise Usage(msg)
        
        # option processing
        for option, value in opts:
            if option == '--clean':
                should_clean = True
                del(argv[argv.index(option)])
            if option in ('-h', '--help'):
                raise Usage(HELP_MESSAGE)
            if option in ('-r', '--revision'):
                revision = value
                del(argv[argv.index(option)])
                del(argv[argv.index(value)])
            if option in ('-w', '--wait'):
                wait = True
                del(argv[argv.index(option)])
            if option in ('-v', '--verbose'):
                verbose = True
                del(argv[argv.index(option)])
    except Usage as err:
        print(f"{sys.argv[0].split('/')[-1]}: {err.msg}", file=sys.stderr)
        print(HELP_MESSAGE, file=sys.stderr)
        return 2
    
    if should_clean:
        return clean_temp_files(verbose)
    file_names = argv[1:]
    for file_name in file_names:
        normalized_file = os.path.normpath(file_name)
        git_path = normalized_file
        if verbose:
            print(f'-> working on {normalized_file}')
        if not os.path.isfile(normalized_file):
            #if verbose:
            print(f'{normalized_file} is not a file')
            continue
        # make sure the file is in the git repository
        try:
            p = subprocess.Popen('git status %s' % normalized_file, 
                                 env=os.environ,
                                 shell=True,
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT)
            p.wait()
            lines = p.stdout.readlines()
            if p.returncode > 0:
                # the file is probably not in the git repo
                # or is not changed, let's find out
                if lines[0].startswith('error:'):
                    print(f'{normalized_file} not in git repository.....skipping')
                    continue
                elif lines[0].startswith('# '):
                    # we're probably not changed
                    if verbose:
                        print(f'    {normalized_file} unchanged.....skipping')
                    continue
            # our file is there, look for the full path to it
            for line in lines:
                line = line.rstrip()
                if line.endswith(normalized_file):
                    # split on the three spaces between 
                    #'modified:' and the file name
                    git_path = line.split('   ')[-1]
                    if verbose:
                        print(f'    git path: {git_path}')
                    break
        except OSError as e:
            print('Execution failed:', e, file=sys.stderr)
        # shadow the requested version of the file to a temp file
        # so we have something to diff against
        temp_file = None
        try:
            p = subprocess.Popen('git show %s:%s' % (revision,git_path), 
                                 env=os.environ,
                                 shell=True,
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT)
            p.wait()
            # git show, it appears, doesn't return a 1 when the
            # revision/tag isn't valid so we have to scan the output
            lines = p.stdout.readlines()
            if lines[0].startswith('fatal:') or lines[0].startswith('error:'):
                print(f'problem getting revision {revision} of file {normalized_file}')
                print(f'    {lines[0]}')
                continue
            else:
                # save the file out
                temp_file = tempfile.mkstemp(TEMP_FILE_SUFFIX, 
                                         TEMP_FILE_PREFIX, 
                                         TEMP_DIRECTORY)
                if verbose:
                    print(f'    temp file: {temp_file[1]}')
                with os.fdopen(temp_file[0], 'w') as temp_fp:
                    temp_fp.write(''.join(lines))
        except OSError as e:
            print('Execution failed:', e, file=sys.stderr)
        # now that we have the temp file we can diff it with the
        # current file in the repo
        try:
            wait_flag = ''
            if wait:
                wait_flag = '--wait'
            p = subprocess.Popen('chdiff %s %s %s' % (wait_flag,
                                                      temp_file[1],
                                                      normalized_file),
                                 env=os.environ,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            p.wait()
            # ugh, this is sloppy, but we only know to clean up
            # if a chdiff wait is specified, so tidy up now
            if wait:
                os.unlink(temp_file[1])
        except OSError as e:
            print('Execution failed:', e, file=sys.stderr)

if __name__ == '__main__':
    sys.exit(main())
    