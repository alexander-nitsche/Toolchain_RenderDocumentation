#!/usr/bin/env python
# coding: utf-8

# ==================================================
# open
# --------------------------------------------------

from __future__ import print_function
import os
import tct
import sys

params = tct.readjson(sys.argv[1])
facts = tct.readjson(params['factsfile'])
milestones = tct.readjson(params['milestonesfile'])
resultfile = params['resultfile']
result = tct.readjson(resultfile)
toolname = params["toolname"]
toolname_short = os.path.splitext(toolname)[0][4:]  # run_01-Name.py -> 01-Name
workdir = params['workdir']
loglist = result['loglist'] = result.get('loglist', [])
exitcode = CONTINUE = 0

# ==================================================
# define
# --------------------------------------------------

xeq_name_cnt = 0

# ==================================================
# Get and check required milestone(s)
# --------------------------------------------------

def milestones_get(name, default=None):
    result = milestones.get(name, default)
    loglist.append((name, result))
    return result

def facts_get(name, default=None):
    result = facts.get(name, default)
    loglist.append((name, result))
    return result

def params_get(name, default=None):
    result = params.get(name, default)
    loglist.append((name, result))
    return result

if exitcode == CONTINUE:
    loglist.append('CHECK PARAMS')
    masterdoc = milestones_get('masterdoc')
    TheProjectMakedir = milestones_get('TheProjectMakedir')

if exitcode == CONTINUE:
    loglist.append('PARAMS are ok')
else:
    loglist.append('PROBLEMS with params')

if not (masterdoc and TheProjectMakedir):
    loglist.append('SKIPPING, because some PARAMS are empty.')
    CONTINUE = -1

# ==================================================
# work
# --------------------------------------------------

import shutil
import codecs

if exitcode == CONTINUE:
    buildsettingssh_file = os.path.join(TheProjectMakedir, 'buildsettings.sh')
    original = buildsettingssh_file + '.original'
    shutil.move(buildsettingssh_file, original)

if exitcode == CONTINUE:

    masterdoc_without_fileext = os.path.splitext(masterdoc)[0]
    with codecs.open(original, 'r', 'utf-8') as f1:
        with codecs.open(buildsettingssh_file, 'w', 'utf-8') as f2:
            for line in f1:
                if line.startswith('MASTERDOC='):
                    line = 'MASTERDOC=' + masterdoc_without_fileext + '\n'
                f2.write(line)

# ==================================================
# Set MILESTONE
# --------------------------------------------------

if exitcode == CONTINUE:
    result['MILESTONES'].append('buildsettings_file_fixed')

# ==================================================
# save result
# --------------------------------------------------

tct.writejson(result, resultfile)

# ==================================================
# Return with proper exitcode
# --------------------------------------------------

sys.exit(exitcode)
