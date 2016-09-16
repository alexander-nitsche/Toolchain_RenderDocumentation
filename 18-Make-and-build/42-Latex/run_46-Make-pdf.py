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
toolname_pure = params["toolname_pure"]
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
    latex_file_folder = milestones_get('latex_file_folder')
    latex_file_tweaked = milestones_get('latex_file_tweaked')
    latex_make_file_tweaked  = milestones_get('latex_make_file_tweaked')
    toolname = params_get('toolname')
    if not (latex_file_folder and latex_file_tweaked and
            latex_make_file_tweaked and toolname):
        exitcode = 2

if exitcode == CONTINUE:
    loglist.append('PARAMS are ok')
else:
    loglist.append('PROBLEM with params')

# ==================================================
# work
# --------------------------------------------------

if exitcode == CONTINUE:

    import codecs
    import subprocess

    workdir = params['workdir']

    def cmdline(cmd, cwd=None):
        if cwd is None:
            cwd = os.getcwd()
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=cwd)
        out, err = process.communicate()
        exitcode = process.returncode
        return exitcode, cmd, out, err

    cmd = 'make -C "' + latex_file_folder + '" all-pdf'

    exitcode, cmd, out, err = cmdline(cmd, cwd=latex_file_folder)

    loglist.append([exitcode, cmd, out, err])

    xeq_name_cnt += 1
    filename_cmd = 'xeq-%s-%d-%s.txt' % (toolname_pure, xeq_name_cnt, 'cmd')
    filename_err = 'xeq-%s-%d-%s.txt' % (toolname_pure, xeq_name_cnt, 'err')
    filename_out = 'xeq-%s-%d-%s.txt' % (toolname_pure, xeq_name_cnt, 'out')
    with codecs.open(os.path.join(workdir, filename_cmd), 'w', 'utf-8') as f2:
        f2.write(cmd.decode('utf-8', 'replace'))
    with codecs.open(os.path.join(workdir, filename_out), 'w', 'utf-8') as f2:
        f2.write(out.decode('utf-8', 'replace'))
    with codecs.open(os.path.join(workdir, filename_err), 'w', 'utf-8') as f2:
        f2.write(err.decode('utf-8', 'replace'))

if exitcode == CONTINUE:

    PROJECT_pdf_file = os.path.join(latex_file_folder, 'PROJECT.pdf')
    if os.path.exists(PROJECT_pdf_file):
        pdf_file = PROJECT_pdf_file

    PROJECT_log_file = os.path.join(latex_file_folder, 'PROJECT.log')
    if os.path.exists(PROJECT_log_file):
        pdf_log_file = PROJECT_log_file



# ==================================================
# Set MILESTONE
# --------------------------------------------------

if exitcode == CONTINUE:
    builds_successful = milestones.get('builds_successful', [])
    builds_successful.append('pdf')
    result['MILESTONES'].append({
        'pdf_file': pdf_file,
        'pdf_log_file': pdf_log_file,
        'build_pdf': 'success',
        'builds_successful': builds_successful,
    })

# ==================================================
# save result
# --------------------------------------------------

tct.writejson(result, resultfile)

# ==================================================
# Return with proper exitcode
# --------------------------------------------------

sys.exit(exitcode)