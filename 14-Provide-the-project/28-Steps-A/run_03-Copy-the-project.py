#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function
from __future__ import absolute_import

import codecs
import os
import subprocess
import sys
import tct

from tct import deepget
from os.path import join as ospj, exists as ospe

params = tct.readjson(sys.argv[1])
facts = tct.readjson(params['factsfile'])
milestones = tct.readjson(params['milestonesfile'])
reason = ''
resultfile = params['resultfile']
result = tct.readjson(resultfile)
toolname = params['toolname']
toolname_pure = params['toolname_pure']
toolchain_name = facts['toolchain_name']
workdir = params['workdir']
loglist = result['loglist'] = result.get('loglist', [])
initial_working_dir = facts['initial_working_dir']
exitcode = CONTINUE = 0


# ==================================================0
# Make a copy of milestones for later inspection?
# --------------------------------------------------

if 0 or milestones.get('debug_always_make_milestones_snapshot'):
    tct.make_snapshot_of_milestones(params['milestonesfile'], sys.argv[1])


# ==================================================
# Helper functions
# --------------------------------------------------

def lookup(D, *keys, **kwdargs):
    result = deepget(D, *keys, **kwdargs)
    loglist.append((keys, result))
    return result


# ==================================================
# define
# --------------------------------------------------

get_documentation_failed = []
get_documentation_succeded = []
TheProject = None
xeq_name_cnt = 0

# ==================================================
# Check params
# --------------------------------------------------

if exitcode == CONTINUE:
    loglist.append('CHECK PARAMS')

    get_documentation_defaults = lookup(milestones,
                                        'get_documentation_defaults',
                                        default=[])
    gitdir = lookup(milestones, 'buildsettings', 'gitdir')
    masterdocs_initial = lookup(milestones, 'masterdocs_initial')
    workdir_home = lookup(params, 'workdir_home')

    if not (1
        and get_documentation_defaults
        and gitdir
        and masterdocs_initial
        and workdir_home
    ):
        exitcode = 22
        reason = 'Bad PARAMS or nothing to do'

if exitcode == CONTINUE:
    loglist.append('PARAMS are ok')
else:
    loglist.append('Bad PARAMS or nothing to do')


# ==================================================
# functions
# --------------------------------------------------

def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


# ==================================================
# Documentation
# --------------------------------------------------

somedoc = """

# Example of section in Settings.cfg:

[get-documentation]

# what to keep of the original project "PROJECT" for the documentation
# rendering process "TheProject". Executed in alphabetical order (!)
# of the key names (anyname_* in this example)

anyname_01 = /PROJECT/README.md           => /TheProject/
anyname_02 = /PROJECT/*                   => /TheProject/
anyname_03 = /PROJECT/Documentation/**/*  => /TheProject/Documentation/
anyname_04 = /PROJECT/Classes/**/*.php    => /TheProject/Classes/


# Components of source specification:
# "", "PROJECT", "path", ["to", ["srcfiles", […,]]] ["**", ] "file pattern"
# Components of dest specification:
# "", "TheProject" [, "path", "to","destfiles"], ""
# Examples:
#    source file or file pattern           destination folder
#    ================================== == ============================
#    (1) /PROJECT/README.md                 => /TheProject/
#    (2) /PROJECT/*                         => /TheProject/
#    (3) /PROJECT/Documentation/**/*        => /TheProject/Documentation/
#    (4) /PROJECT/Classes/**/*.php          => /TheProject/Classes/

#    Explanation:
#       (1) just one file, (2) all files, (3) all files, recursive
#       (4) all *.php files, recursive

"""

# ==================================================
# classes
# --------------------------------------------------

class RsyncJob:
    """Deal with and rsync job string"""

    def __init__(self, job, rsync_options="-a", srcbase='/PROJECT',
                                             destbase='/TheProject'):
        self.cmdparts = []
        self.destbase = destbase.replace('\\', '/').rstrip('/')
        self.destpath = None
        self.file_pattern = None
        self.is_wild = None
        self.job = job
        self.rsync_options = rsync_options
        self.reasons = []
        self.recursive = None
        self.srcbase = srcbase.replace('\\', '/').rstrip('/')
        self.srcpath = None
        self.valid = False

        self.leftparts = None
        self.rightparts = None

        proceed = True
        if proceed:
            splitted = job.split(' => ')
            proceed = len(splitted) == 2
            if not proceed:
                self.reasons.append("expecting exactly one ' => '")
        if proceed:
            left = splitted[0].strip()
            proceed = not not left
            if not proceed:
                self.reasons.append("source is missing")
        if proceed:
            proceed = left.startswith('/PROJECT/')
            if not proceed:
                self.reasons.append("source needs to start with '/PROJECT/'")
        if proceed:
            self.rightstr = splitted[1].strip().rstrip('/')
            proceed = not not self.rightstr
            if not proceed:
                self.reasons.append("destination is missing")
        if proceed:
            if '*' in self.rightstr or '?' in self.rightstr:
                proceed = False
                self.reasons.append("destpath must not contain wildcards")
        if proceed:
            proceed = (self.rightstr + '/').startswith('/TheProject/')
            if not proceed:
                self.reasons.append("first part of destination must be '/TheProject'")

        # file specification
        if proceed:
            self.leftparts = splitall(left)
            proceed = len(self.leftparts) > 2
            if not proceed:
                self.reasons.append("source file specification is missing")
        if proceed:
            self.file_pattern = self.leftparts.pop()
            self.is_wild = '*' in self.file_pattern or '?' in self.file_pattern
            proceed = self.file_pattern != ''
            if not proceed:
                self.reasons.append('no source file(s) specified')

        # recursive?
        if proceed and len(self.leftparts) > 2:
            self.recursive = self.leftparts[-1] == '**'
            if self.recursive:
                self.leftparts.pop()

        if proceed:
            self.leftstr = os.path.join(*self.leftparts)
            if '*' in self.leftstr or '?' in self.leftstr:
                proceed = False
                self.reasons.append("effective srcpath must not contain wildcards")

        if proceed:
            segment = self.leftstr[9:]
            if segment:
                self.srcpath = os.path.join(self.srcbase, segment)
            else:
                self.srcpath = self.srcbase
            segment = self.rightstr[12:]
            if segment:
                self.destpath = os.path.join(self.destbase, segment)
            else:
                self.destpath = self.destbase

        # use

        if proceed:
            self.cmdparts.append('rsync')
            if self.rsync_options:
                self.cmdparts.append(self.rsync_options)
            if not self.recursive:
                self.cmdparts.append('--exclude="*/"')
            if self.file_pattern != '*':
                self.cmdparts.append('--include="%s"' % self.file_pattern)
                if self.recursive:
                    self.cmdparts.append('--include="*/"')
                self.cmdparts.append('--exclude="*"')
            if self.recursive:
                self.cmdparts.append('--prune-empty-dirs')
            self.cmdparts.append(self.srcpath + '/')
            self.cmdparts.append(self.destpath + '/')

        if proceed:
            self.valid = True

        return

    def dump(self, force=None):
        print('==== RsyncJob BEGIN ====')

        if self.valid or force:
            print('#', self.job)
            print('# recursive:', repr(self.recursive))
            print('# is_wild:', repr(self.is_wild))
            print(' \\\n   '.join(self.cmdparts))

        if not self.valid or force:
            print('valid        :', repr(self.valid))
            print('reasons      :', repr(self.reasons))

            print('job          :', repr(self.job))
            print('srcpath      :', repr(self.srcpath))
            print('is_wild      :', repr(self.is_wild))
            print('file_pattern :', repr(self.file_pattern))
            print('destpath     :', repr(self.destpath))

            print('rsync_options:', repr(self.rsync_options))
            print('recursive    :', repr(self.recursive))
            print('cmdparts     :', repr(self.cmdparts))
        print('==== RsyncJob END ====')

# ==================================================
# we want to call the shell
# --------------------------------------------------

if exitcode == CONTINUE:

    def cmdline(cmd, cwd=None):
        if cwd is None:
            cwd = os.getcwd()
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=cwd)
        out, err = process.communicate()
        exitcode = process.returncode
        return exitcode, cmd, out, err

    def execute_cmdlist(cmdlist, cwd=None):
        global xeq_name_cnt
        cmd = ' '.join(cmdlist)
        cmd_multiline = ' \\\n   '.join(cmdlist) + '\n'

        xeq_name_cnt += 1
        filename_cmd = 'xeq-%s-%d-%s.txt' % (toolname_pure, xeq_name_cnt, 'cmd')
        filename_err = 'xeq-%s-%d-%s.txt' % (toolname_pure, xeq_name_cnt, 'err')
        filename_out = 'xeq-%s-%d-%s.txt' % (toolname_pure, xeq_name_cnt, 'out')

        with codecs.open(os.path.join(workdir, filename_cmd), 'w', 'utf-8') as f2:
            f2.write(cmd_multiline.decode('utf-8', 'replace'))

        exitcode, cmd, out, err = cmdline(cmd, cwd=cwd)

        loglist.append({'exitcode': exitcode, 'cmd': cmd, 'out': out, 'err': err})

        with codecs.open(os.path.join(workdir, filename_out), 'w', 'utf-8') as f2:
            f2.write(out.decode('utf-8', 'replace'))

        with codecs.open(os.path.join(workdir, filename_err), 'w', 'utf-8') as f2:
            f2.write(err.decode('utf-8', 'replace'))

        return exitcode, cmd, out, err

# ==================================================
# work
# --------------------------------------------------

if exitcode == CONTINUE:
    TheProject = os.path.join(workdir_home, 'TheProject')
    if not os.path.exists(TheProject):
        os.mkdir(TheProject)

    srcdir = gitdir.replace('\\', '/').rstrip('/')
    stresstest_lines = [
        '/PROJECT/README.md           => /TheProject',
        '/PROJECT/**/README.md        => /TheProject',
        '/PROJECT/*                   => /TheProject',
        '/PROJECT/Documentation/**/*  => /TheProject/Documentation',
        '/PROJECT/Classes/**/*.php    => /TheProject/Classes',
        '/PROJECT/None/**/*.php       => /TheProject/None',
        '/PROJECT/**/*                => /TheProject/all-for-inspection',
        '/PROJECT/**/*.xml            => /TheProject/all-xml',
    ]
    planned = get_documentation_defaults
    rsync_options = '-a'
    stresstest = False

    if 0 and 'stresstest':
        stresstest = True
        planned.extend(stresstest_lines)
        rsync_options = '-avii'

    for jobstr in planned:
        job = RsyncJob(jobstr, rsync_options, srcdir, TheProject)
        if stresstest:
            job.dump('print all to stdout')
        if not job.valid:
            get_documentation_failed.append((jobstr, job.reasons))
            continue
        if not ospe(job.srcpath):
            get_documentation_failed.append((jobstr,
                                             ['source folder not found']))
            continue
        if not ospe(job.destpath):
            os.makedirs(job.destpath)
        tmp_exitcode, cmd, out, err = execute_cmdlist(job.cmdparts,
                                                      cwd=workdir)
        if tmp_exitcode == 0:
            get_documentation_succeded.append(jobstr)
        else:
            get_documentation_failed.append(
                (jobstr, ['rsync finished with exitcode: %s' % tmp_exitcode]))


# ==================================================
# Set MILESTONE
# --------------------------------------------------

if TheProject:
    result['MILESTONES'].append({'TheProject':
                                 TheProject})

if get_documentation_failed:
    temp = lookup(milestones, 'get_documentation_failed', default=[])
    if temp:
        get_documentation_failed = temp + get_documentation_failed
    result['MILESTONES'].append({'get_documentation_failed':
                                 get_documentation_failed})

if get_documentation_succeded:
    temp = lookup(milestones, 'get_documentation_succeded', default=[])
    if temp:
        get_documentation_succeded = temp + get_documentation_succeded
    result['MILESTONES'].append({'get_documentation_succeded':
                                 get_documentation_succeded})


# ==================================================
# save result
# --------------------------------------------------

tct.save_the_result(result, resultfile, params, facts, milestones, exitcode, CONTINUE, reason)

# ==================================================
# Return with proper exitcode
# --------------------------------------------------

sys.exit(exitcode)
