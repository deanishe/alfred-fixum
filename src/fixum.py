#!/usr/bin/python
# encoding: utf-8
#
# Copyright (c) 2017 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2017-04-03
#

"""fixum [options]

Usage:
    fixum list <query>
    fixum [-n]
    fixum -h|--help
    fixum --version

Options:
    -n, --nothing   Dry run. Don't actually change any workflow.
    -h, --help      Show this message and exit.
    --version       Show version number and exit.

"""

from __future__ import print_function, absolute_import

from collections import namedtuple
from fnmatch import fnmatch
import os
import plistlib
import shutil
import subprocess
import sys

import docopt
from workflow import (
    ICON_WARNING,
    MATCH_STARTSWITH,
    MATCH_CAPITALS,
    MATCH_ATOM,
    MATCH_INITIALS_STARTSWITH,
    MATCH_SUBSTRING,
    Workflow3,
)
from workflow.update import Version


log = None

ICON_UPDATE = 'update-available.png'

# version of AW in this workflow
VERSION_FILE = os.path.join(os.path.dirname(__file__), 'workflow/version')
MIN_VERSION = Version(open(VERSION_FILE).read())

# path to good copy of Alfred-Workflow
WF_DIR = os.path.join(os.path.dirname(__file__), 'workflow')

# Alfred 3 preferences property list. Contains path to workflow
# directory
ALFRED_PREFS = os.path.expanduser(
    '~/Library/Preferences/com.runningwithcrayons.Alfred-Preferences-3.plist')

# Initial values for `settings.json`
DEFAULT_SETTINGS = {}

# Auto-update from GitHub releases
UPDATE_SETTINGS = {
    'github_slug': 'deanishe/alfred-fixum',
}

HELP_URL = 'https://github.com/deanishe/alfred-fixum/issues'

MATCH = (MATCH_STARTSWITH |
         MATCH_CAPITALS |
         MATCH_ATOM |
         MATCH_INITIALS_STARTSWITH |
         MATCH_SUBSTRING)

Workflow = namedtuple('Workflow', 'name id dir aw')
AWInfo = namedtuple('AWInfo', 'dir version')


def touch(path):
    """Set mtime and atime of ``path`` to now."""
    with open(path, 'a'):
        os.utime(path, None)


def read_plist(path):
    """Convert plist to XML and read its contents."""
    if isinstance(path, unicode):
        path = path.encode('utf-8')

    cmd = ['plutil', '-convert', 'xml1', '-o', '-', path]
    xml = subprocess.check_output(cmd)
    return plistlib.readPlistFromString(xml)


def get_aw_info(dirpath):
    """Return version and directory of AW if it's installed."""
    candidates = []
    for root, _, filenames in os.walk(dirpath):
        if 'workflow.py' in filenames and os.path.basename(root) == 'workflow':
            candidates.append(root)

    for dp in candidates:
        wp = os.path.join(dp, 'workflow.py')
        vp = os.path.join(dp, 'version')

        with open(wp) as fp:
            text = fp.read()
        if 'Dean Jackson <deanishe@deanishe.net>' not in text:
            log.debug('non-AW workflow.py ignored')
            continue

        if os.path.exists(vp):
            with open(vp) as fp:
                v = Version(fp.read().strip())
        else:
            log.warning('no version file in %s, assuming a very old version',
                        dirpath)
            v = Version('0.0.1')

        return AWInfo(dp, v)

    return None


def get_workflow_info(dirpath):
    """Extract some workflow information from info.plist."""
    ip = os.path.join(dirpath, 'info.plist')
    if not os.path.exists(ip):
        return None

    info = read_plist(ip)
    name = info['name']
    bid = info['bundleid']
    if not bid:  # can't be an AW workflow - it requires a bundle ID
        return None

    aw = get_aw_info(dirpath)
    if not aw:
        return None

    return Workflow(name, bid, dirpath, aw)


def get_workflow_directory():
    """Return path to Alfred's workflow directory."""
    # It appears that `syncfolder` may be set but not used
    # https://github.com/deanishe/alfred-fixum/issues/8
    # So don't trust `syncfolder` and fall back to the default
    # location, and if that fails, the grandparent of the working
    # directory.
    candidates = []

    # User-specified sync directory
    prefs = read_plist(ALFRED_PREFS)
    syncdir = prefs.get('syncfolder')
    if syncdir:
        candidates.append(syncdir)

    # Default location
    candidates.append('~/Library/Application Support/Alfred 3')

    # Workflows are run with their own directory as the working path,
    # so try grandparent as last resort (if workflow is being run
    # from Alfred)
    if os.getenv('alfred_version'):
        candidates.append(
            os.path.dirname(os.path.dirname(os.path.abspath(os.curdir))))
    else:
        log.warning('workflow is not being run from Alfred')

    candidates = [os.path.expanduser(p) for p in candidates]

    for path in candidates:
        log.debug('looking for workflows in %r ...', path)
        wf_dir = os.path.join(path, 'Alfred.alfredpreferences/workflows')
        if os.path.exists(wf_dir):
            return wf_dir

    log.debug('workflow directory not found')
    return None


def load_blacklist():
    """Load bundle IDs of blacklisted workflows."""
    blacklisted = []
    p = wf.datafile('blacklist.txt')
    if os.path.exists(p):
        with open(p) as fp:
            for line in fp:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                blacklisted.append(line)

    return blacklisted


def _newname(path):
    """Return new, unused name by adding digits."""
    i = 1
    newpath = path

    while os.path.exists(newpath):
        newpath = '{}.{}'.format(path, i)
        i += 1

    return newpath


def update_workflow(info):
    """Replace outdated version of Alfred-Workflow."""
    log.info('    updating "%s" ...', info.name)
    newdir = _newname(info.aw.dir + '.old')
    log.debug('    moving %s to %s ...', info.aw.dir, newdir)
    os.rename(info.aw.dir, newdir)
    log.debug('    copying new version of AW to %s ...', info.aw.dir)
    shutil.copytree(WF_DIR, info.aw.dir)
    log.info('    installed new version of Alfred-Workflow')

    # Create file to let Alfred know this workflow is okay
    open(os.path.join(info.aw.dir, '.alfredversionchecked'), 'w')

    # Touch info.plist to let Alfred know this workflow has been updated
    touch(os.path.join(info.dir, 'info.plist'))


def list_actions(opts):
    """Show available workflow actions."""
    query = opts['<query>']
    log.debug('query=%r', query)

    if wf.update_available:
        wf.add_item('A newer version of Fixum is available',
                    u'⇥ or ↩ to install update',
                    valid=False,
                    autocomplete='workflow:update',
                    icon=ICON_UPDATE)

    items = [
        dict(title='Dry Run',
             subtitle='Show what the workflow would update',
             arg='dryrun',
             uid='dryrun',
             valid=True),
        dict(title='View Log File',
             subtitle='Open the log file in Console.app',
             arg='log',
             uid='log',
             valid=True),
        dict(title='Edit Blacklist',
             subtitle='List of workflows to *not* update',
             arg='blacklist',
             uid='blacklist',
             valid=True),
        dict(title='Fix Workflows',
             subtitle=('Replace broken versions of Alfred-Workflow '
                       'within your workflows'),
             arg='fix',
             uid='fix',
             valid=True),
    ]

    if query:
        items = wf.filter(query, items, key=lambda d: d['title'],
                          match_on=MATCH, min_score=50)

    if not items:
        wf.add_item('No matching actions', 'Try a different query',
                    icon=ICON_WARNING)

    for d in items:
        wf.add_item(**d)

    wf.send_feedback()


def main(wf):
    """Run workflow script."""
    opts = docopt.docopt(__doc__, argv=wf.args, version=wf.version)
    if opts['list']:
        return list_actions(opts)

    dry_run = opts['--nothing']
    log.info('=' * 50)
    log.debug('opts=%r', opts)
    log.info('looking for workflows using an outdated version '
             'of Alfred-Workflow...')

    # subprocess.call(['open', '-a', 'Console', wf.logfile])

    root = get_workflow_directory()
    if not root:
        log.critical('could not find your workflow directory')
        print('ERROR: could not find workflow directory')
        return 1

    log.info('workflow directory: %r', root)

    blacklisted = load_blacklist()

    updated = 0
    failed = 0

    # loop through subdirectories of workflow directory
    #   1. ignore symlinks
    #   2. ignore files
    #   3. ignore blacklisted workflows
    #   4. identify AW workflows
    #   5. check version of AW the workflow has
    #   6. if AW is outdated, backup the existing copy and replace
    #      it with an up-to-date version of AW
    for dn in os.listdir(root):
        p = os.path.join(root, dn)
        if os.path.islink(p):
            log.info('ignoring symlink: %s', dn)
            continue

        if not os.path.isdir(p):
            log.debug('ignoring non-directory: %s', dn)
            continue

        try:
            info = get_workflow_info(p)
        except Exception as err:
            log.error('could not read workflow: %s: %s', dn, err)
            continue

        if not info or not info.aw.dir:
            log.debug('not an AW workflow: %s', dn)
            continue

        if info.id == wf.bundleid:
            log.debug('ignoring self')
            continue

        ok = True
        for pat in blacklisted:
            if fnmatch(info.id, pat):
                log.debug('blacklisted: "%s" matches "%s"', info.id, pat)
                log.info('skipping blacklisted workflow: %s', dn)
                ok = False
                break

        if not ok:
            continue

        log.info('')
        log.info('found AW workflow: %s', dn)
        log.info('             name: %s', info.name)
        log.info('        bundle ID: %s', info.id)
        log.info('       AW version: %s', info.aw.version)

        if info.aw.version >= MIN_VERSION:
            log.info('[OK] workflow "%s" has current version of '
                     'Alfred-Workflow', info.name)
            log.info('')
            continue

        log.info('[!!] workflow "%s" is using outdated version '
                 '(%s) of Alfred-Workflow', info.name, info.aw.version)

        if not dry_run:
            try:
                update_workflow(info)
            except Exception as err:
                failed += 1
                log.error('failed to update workflow "%s" (%s): %s',
                          info.name, info.aw.dir, err, exc_info=True)
                log.info('')
                continue

        log.info('')

        updated += 1

    if dry_run:
        log.info('[DONE] would update %d workflow(s) with a newer version of '
                 'Alfred-Workflow', updated)
        print('Would update {} workflow(s)'.format(updated))
        return

    else:
        if failed:
            log.info('[DONE] failed to update %d/%d workflow(s) with a '
                     'newer version of Alfred-Workflow',
                     failed, failed + updated)
            print('ERROR: Failed to update {}/{} workflow(s)'.format(
                  failed, failed + updated))
            return 1
        else:
            log.info('[DONE] updated %d workflow(s) with a newer version of '
                     'Alfred-Workflow', updated)
            print('Updated {} workflow(s)'.format(updated))

    return


if __name__ == '__main__':
    wf = Workflow3(
        default_settings=DEFAULT_SETTINGS,
        update_settings=UPDATE_SETTINGS,
        help_url=HELP_URL,
    )
    log = wf.logger
    sys.exit(wf.run(main, text_errors=True))
