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
loglist = result['loglist'] = result.get('loglist', [])
exitcode = CONTINUE = 0

# ==================================================
# Get and check required milestone(s)
# --------------------------------------------------

def milestones_get(name, default=None):
    result = milestones.get(name, default)
    loglist.append((name, result))
    return result

if exitcode == CONTINUE:
    tools_exitcodes = facts.get('tools_exitcodes')
    publish_dir_buildinfo = milestones_get('publish_dir_buildinfo')
    if not (publish_dir_buildinfo and tools_exitcodes):
        exitcode = 2

# ==================================================
# work
# --------------------------------------------------

if exitcode == CONTINUE:

    D = {}
    cnt = 0
    for k in sorted(tools_exitcodes):
        cnt += 1
        v = tools_exitcodes[k]
        k2 = '%3d | %3s | %s' % (cnt, v, k)
        D[k2] = v

    publish_dir_buildinfo_exitcodes = os.path.join(publish_dir_buildinfo, 'exitcodes.json')
    tct.writejson(D, publish_dir_buildinfo_exitcodes)


# ==================================================
# Set MILESTONE
# --------------------------------------------------

if exitcode == CONTINUE:
    result['MILESTONES'].append({
        'publish_dir_buildinfo_exitcodes': publish_dir_buildinfo_exitcodes})

# ==================================================
# save result
# --------------------------------------------------

tct.writejson(result, resultfile)

# ==================================================
# Return with proper exitcode
# --------------------------------------------------

sys.exit(exitcode)
