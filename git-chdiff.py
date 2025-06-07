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

help_message = '''
git-chdiff <opts> [file1, file2, ...]

display diffs of git files using the chdiff utility 

  -h, --help        display this message
  -r, --revision    the revision of the file to use 
                       defaults to 'HEAD~1', the previous commit
  -w, --wait        cause chdiff to wait between files
  -v, --verbose     print more messages during operation
  --clean           clean any temp files that might have been left around
'''

tempFileSuffix = '.temp'
tempFilePrefix = 'git-chdiff'
tempDirectory = '/var/tmp'

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def cleanTempFiles(verbose=False):
    """
    because we don't always wait for chdiff we can't always clean up
    the temp files we make.  This will wipe out all git-chdiff temp
    files owned by us.
    """

    try:
        if verbose:
            print('scanning for git-chdiff temp files to clean')
        myUid = pwd.getpwnam(getpass.getuser())[2]
        fileList = os.listdir(tempDirectory)
        for fileName in fileList:
            nFile = os.path.join(tempDirectory, fileName)
            # skip directories
            if not os.path.isfile(nFile):
                continue
            # skip anything not named right
            if not fileName.startswith(tempFilePrefix):
                continue
            # skip if it's not our file
            if os.stat(nFile)[4] != myUid:
                continue
            # if we're here we own the file and it's named correctly
            # remove it
            if verbose:
                print('removing temp file: %s' % nFile)
            os.unlink(nFile)
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
    doClean = False
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
                doClean = True
                del(argv[argv.index(option)])
            if option in ('-h', '--help'):
                raise Usage(help_message)
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
        print(help_message, file=sys.stderr)
        return 2
    
    if doClean:
        return cleanTempFiles(verbose)
    fileNames = argv[1:]
    for fileName in fileNames:
        nFile = os.path.normpath(fileName)
        gitFile = nFile
        if verbose:
            print(f'-> working on {nFile}')
        if not os.path.isfile(nFile):
            #if verbose:
            print(f'{nFile} is not a file')
            continue
        # make sure the file is in the git repository
        try:
            p = subprocess.Popen('git status %s' % nFile, 
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
                    print(f'{nFile} not in git repository.....skipping')
                    continue
                elif lines[0].startswith('# '):
                    # we're probably not changed
                    if verbose:
                        print(f'    {nFile} unchanged.....skipping')
                    continue
            # our file is there, look for the full path to it
            for line in lines:
                line = line.rstrip()
                if line.endswith(nFile):
                    # split on the three spaces between 
                    #'modified:' and the file name
                    gitFile = line.split('   ')[-1]
                    if verbose:
                        print(f'    git path: {gitFile}')
                    break
        except OSError as e:
            print('Execution failed:', e, file=sys.stderr)
        # shadow the requested version of the file to a temp file
        # so we have something to diff against
        tFile = None
        try:
            p = subprocess.Popen('git show %s:%s' % (revision,gitFile), 
                                 env=os.environ,
                                 shell=True,
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT)
            p.wait()
            # git show, it appears, doesn't return a 1 when the
            # revision/tag isn't valid so we have to scan the output
            lines = p.stdout.readlines()
            if lines[0].startswith('fatal:') or lines[0].startswith('error:'):
                print(f'problem getting revision {revision} of file {nFile}')
                print(f'    {lines[0]}')
                continue
            else:
                # save the file out
                tFile = tempfile.mkstemp(tempFileSuffix, 
                                         tempFilePrefix, 
                                         tempDirectory)
                if verbose:
                    print(f'    temp file: {tFile[1]}')
                with os.fdopen(tFile[0], 'w') as temp_fp:
                    temp_fp.write(''.join(lines))
        except OSError as e:
            print('Execution failed:', e, file=sys.stderr)
        # now that we have the temp file we can diff it with the
        # current file in the repo
        try:
            waitFlag = ''
            if wait:
                waitFlag = '--wait'
            p = subprocess.Popen('chdiff %s %s %s' % (waitFlag,
                                                      tFile[1],
                                                      nFile),
                                 env=os.environ,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            p.wait()
            # ugh, this is sloppy, but we only know to clean up
            # if a chdiff wait is specified, so tidy up now
            if wait:
                os.unlink(tFile[1])
        except OSError as e:
            print('Execution failed:', e, file=sys.stderr)

if __name__ == '__main__':
    sys.exit(main())
