#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function
from __future__ import absolute_import

import codecs
import json
import os
import sys
import tct

from bs4 import BeautifulSoup
from tct import deepget
from urlparse import urlparse

params = tct.readjson(sys.argv[1])
binabspath = sys.argv[2]
facts = tct.readjson(params['factsfile'])
milestones = tct.readjson(params['milestonesfile'])
reason = ''
resultfile = params['resultfile']
result = tct.readjson(resultfile)
loglist = result['loglist'] = result.get('loglist', [])
toolname = params['toolname']
toolname_pure = params['toolname_pure']
workdir = params['workdir']
exitcode = CONTINUE = 0


# ==================================================
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

all_html_files_sanitized = None
all_html_files_sanitized_count = None
all_singlehtml_files_sanitized = None
all_singlehtml_files_sanitized_count = None
neutralized_images = []
neutralized_images_jsonfile = None
neutralized_links = []
neutralized_links_jsonfile = None
postprocessing_is_required = None
replace_static_in_html_done = None
statics_path = None
statics_path_replacement = None
sitemap_files_html = None
sitemap_files_singlehtml = None
xeq_name_cnt = 0

# ==================================================
# Check params
# --------------------------------------------------

if exitcode == CONTINUE:
    loglist.append('CHECK PARAMS')

    # we reuse the sitmap files we already have to identify the html files for
    # postprocessing

    build_html_folder = lookup(milestones, 'build_html_folder', default=None)
    sitemap_files_html_jsonfile = lookup(
        milestones, 'sitemap_files_html_jsonfile', default=None)
    if not (1
            and build_html_folder
            and sitemap_files_html_jsonfile):
        exitcode = 22
        reason = 'Bad PARAMS or nothing to do'

if exitcode == CONTINUE:
    build_singlehtml_folder = lookup(milestones, 'build_singlehtml_folder',
                                     default=None)
    sitemap_files_singlehtml_jsonfile = lookup(
        milestones, 'sitemap_files_singlehtml_jsonfile', default=None)
    if (not build_html_folder) != (not sitemap_files_html_jsonfile):
        exitcode = 22
        reason = 'Either have none or both'
        loglist.append(reason)

if exitcode == CONTINUE:
    loglist.append('PARAMS are ok')
else:
    loglist.append('Bad PARAMS or nothing to do')


# ==================================================
# work
# --------------------------------------------------

def is_valid_version(ver):
    """Make sure the version number is formally valid."""
    result = isinstance(ver, basestring) and not not ver
    if result:
        parts = ver.split('.')
        result = len(parts) == 3
    sum = 0
    if result:
        try:
            for part in parts:
                ipart = int(part)
                sum = sum * 1000 + ipart
        except:
            result = False
    result = result and int(sum/1000/1000) > 0
    return result


if exitcode == CONTINUE:

    html_theme_options = lookup(milestones, "conf_py_settings",
                                "html_theme_options", default={})
    if html_theme_options and not html_theme_options.get("docstypo3org"):
        reason = (
            "We don't do postprocessing, since we do have the\n"
            "Settings.dump.json of the Sphinx html build,\n"
            "but 'docstypo3org' (rendering for server) is not\n"
            "set in there.\n")
        loglist.append(reason)
        CONTINUE = -2

if exitcode == CONTINUE:
    postprocessing_is_required = 1

if exitcode == CONTINUE:
    replace_static_in_html = lookup(milestones, 'replace_static_in_html')
    theme_info = lookup(milestones, 'theme_info')
    # NAME=sphinx_typo3_theme
    # https://typo3.azureedge.net/typo3documentation/theme/<NAME>/<BRANCH|VERSION>/css/theme.css
    # https://typo3.azureedge.net/typo3documentation/theme/sphinx_typo3_theme/4.0.1/css/theme.css
    # https://typo3.azureedge.net/typo3documentation/theme/sphinx_typo3_theme/master/css/theme.css

    statics_path = '_static/'
    statics_path_replacement = (
        'https://typo3.azureedge.net/typo3documentation/'
        'theme/sphinx_typo3_theme/master/')

    if not replace_static_in_html:
        statics_path_replacement = ''
    if statics_path_replacement:
        if lookup(theme_info, 'theme_name') != 'sphinx_typo3_theme':
            statics_path_replacement = ''
            reason = 'no replacement - unknown theme name'
    if statics_path_replacement:
        if not is_valid_version(lookup(theme_info, 'theme_version_core')):
            statics_path_replacement = ''
            reason = 'no replacement - unknown theme version'


def process_html_file(folder, relpath):
    soup_modified = False
    builder = os.path.split(folder)[1]
    abspath = folder + '/' + relpath
    with codecs.open(abspath, 'r', 'utf-8') as f1:
        soup = BeautifulSoup(f1, 'lxml')

    for link in soup.find_all('a'):
        href = link.get('href')
        if href is not None:
            if (href.lower().startswith('javascript:') or
                    href.lower().startswith('data:')):
                logname = builder + '/' + fpath
                neutralized_links.append((logname, href))
                link['href'] = '#'
                soup_modified = True
            else:
                our_hostnames_2 = (['typo3', 'org'], ['typo3', 'com'])
                other_hostnames_3 = (['typo3', 'azureedge', 'net'],
                                     ['app', 'usercentrics', 'eu'])

                o = urlparse(href)
                if o.hostname:
                    # absolute links
                    if o.hostname.split('.')[-2:] not in our_hostnames_2:
                        parts = link.get('rel', [])
                        if 'nofollow' not in parts:
                            parts.append('nofollow')
                        if 'noopener' not in parts:
                            parts.append('noopener')
                        link['rel'] = ' '.join(parts)
                        soup_modified = True

    if statics_path_replacement:
        for link in soup.find_all('link'):
            href = link.get('href')
            if href is not None:
                if href.startswith(statics_path):
                    link['href'] = (statics_path_replacement +
                                    href[len(statics_path):])
                    soup_modified = True

        for script in soup.find_all('script'):
            src = script.get('src')
            if src is not None:
                if src.startswith(statics_path):
                    script['src'] = (statics_path_replacement +
                                     src[len(statics_path):])
                    soup_modified = True

    for img in soup.find_all('img'):
        src = img.get('src')
        if src is not None:
            if (src.lower().startswith('javascript:') or
                    src.lower().startswith('data:')):
                logname = builder + '/' + fpath
                neutralized_images.append((logname, src))
                img['src'] = ''
                soup_modified = True
            elif statics_path_replacement and src.startswith(statics_path):
                img['src'] = (statics_path_replacement +
                              src[len(statics_path):])
                soup_modified = True

    if soup_modified:
        with open(abspath, 'wb') as f2:
            print(soup, file=f2)


if exitcode == CONTINUE:

    if sitemap_files_html_jsonfile:
        all_html_files_sanitized_count = 0
        sitemap_files_html_count = milestones.get('sitemap_files_html_count')
        with codecs.open(sitemap_files_html_jsonfile, 'r', 'utf-8') as f1:
            sitemap_files_html = json.load(f1)
        for fpath in sitemap_files_html:
            process_html_file(build_html_folder.rstrip('/'), fpath)
            all_html_files_sanitized_count += 1
        if all_html_files_sanitized_count == sitemap_files_html_count:
            all_html_files_sanitized = 1

    if sitemap_files_singlehtml_jsonfile:
        all_singlehtml_files_sanitized_count = 0
        sitemap_files_singlehtml_count = milestones.get('sitemap_files_'
                                                        'singlehtml_count')
        with codecs.open(
                sitemap_files_singlehtml_jsonfile, 'r', 'utf-8') as f1:
            sitemap_files_singlehtml = json.load(f1)
        for fpath in sitemap_files_singlehtml:
            process_html_file(build_singlehtml_folder.rstrip('/'), fpath)
            all_singlehtml_files_sanitized_count += 1

        if all_singlehtml_files_sanitized_count == sitemap_files_singlehtml_count:
            all_singlehtml_files_sanitized = 1

if exitcode == CONTINUE:

    if statics_path_replacement:
        replace_static_in_html_done = '1'

    if neutralized_links:
        neutralized_links_jsonfile = os.path.join(workdir,
                                                  'neutralized_links.json')
        with codecs.open(neutralized_links_jsonfile, 'w', 'utf-8') as f2:
            json.dump(neutralized_links, f2)

    if neutralized_images:
        neutralized_images_jsonfile = os.path.join(workdir,
                                                   'neutralized_images.json')
        with codecs.open(neutralized_images_jsonfile, 'w', 'utf-8') as f2:
            json.dump(neutralized_images, f2)


# ==================================================
# Set MILESTONE
# --------------------------------------------------

if all_html_files_sanitized:
    result['MILESTONES'].append({
        'all_html_files_sanitized': all_html_files_sanitized})

if all_html_files_sanitized_count is not None:
    result['MILESTONES'].append({
        'all_html_files_sanitized_count': all_html_files_sanitized_count})

if all_singlehtml_files_sanitized:
    result['MILESTONES'].append({
        'all_singlehtml_files_sanitized': all_singlehtml_files_sanitized})

if all_singlehtml_files_sanitized_count is not None:
    result['MILESTONES'].append({
        'all_singlehtml_files_sanitized_count':
        all_singlehtml_files_sanitized_count})

if neutralized_images_jsonfile:
    result['MILESTONES'].append({
        'neutralized_images_jsonfile': neutralized_images_jsonfile})

if neutralized_links_jsonfile:
    result['MILESTONES'].append({
        'neutralized_links_jsonfile': neutralized_links_jsonfile})

if postprocessing_is_required:
    result['MILESTONES'].append({
        'postprocessing_is_required': postprocessing_is_required})

if statics_path:
    result['MILESTONES'].append({
        'statics_path': statics_path})

if statics_path_replacement:
    result['MILESTONES'].append({
        'statics_path_replacement': statics_path_replacement})

if replace_static_in_html_done:
    result['MILESTONES'].append({
        'replace_static_in_html_done': replace_static_in_html_done})


# ==================================================
# save result
# --------------------------------------------------

tct.save_the_result(result, resultfile, params, facts, milestones, exitcode, CONTINUE, reason)


# ==================================================
# Return with proper exitcode
# --------------------------------------------------

sys.exit(exitcode)
