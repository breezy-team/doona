#    wrapper.py -- Quilt patch handling
#    Copyright (C) 2019-2021 Jelmer Verooij <jelmer@jelmer.uk>
#
#    Breezy is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    Breezy is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Breezy; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

"""Quilt patch handling."""

import errno
import logging
import os
import signal
import subprocess


DEFAULT_PATCHES_DIR = 'patches'
DEFAULT_SERIES_FILE = 'series'


logger = logging.getLogger(__name__)


class QuiltError(Exception):

    _fmt = "An error (%(retcode)d) occurred running quilt: %(stderr)s%(extra)s"

    def __init__(self, retcode, stdout, stderr):
        self.retcode = retcode
        self.stderr = stderr
        if stdout is not None:
            self.extra = "\n\n%s" % stdout
        else:
            self.extra = ""
        self.stdout = stdout


class QuiltNotInstalled(Exception):

    _fmt = "Quilt is not installed."


def run_quilt(
        args, working_dir, series_file=None, patches_dir=None,
        quiet: bool = True):
    """Run quilt.

    Args:
      args: Arguments to quilt
      working_dir: Working dir
      series_file: Optional path to the series file
      patches_dir: Optional path to the patches
      quilt: Whether to be quiet (quilt stderr not to terminal)

    Raises:
      QuiltError: When running quilt fails
    """
    def subprocess_setup():
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    env = {}
    if patches_dir is not None:
        env["QUILT_PATCHES"] = patches_dir
    else:
        env["QUILT_PATCHES"] = os.path.join(working_dir, DEFAULT_PATCHES_DIR)
    if series_file is not None:
        env["QUILT_SERIES"] = series_file
    else:
        env["QUILT_SERIES"] = DEFAULT_SERIES_FILE
    # Hide output if -q is in use.
    if not quiet:
        stderr = subprocess.STDOUT
    else:
        stderr = subprocess.PIPE
    command = ["quilt"] + args
    logger.debug("running: %r", command)
    if not os.path.isdir(working_dir):
        raise AssertionError("%s is not a valid directory" % working_dir)
    try:
        proc = subprocess.Popen(
            command, cwd=working_dir, env=env,
            stdin=subprocess.PIPE, preexec_fn=subprocess_setup,
            stdout=subprocess.PIPE, stderr=stderr)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
        raise QuiltNotInstalled()
    (stdout, stderr) = proc.communicate()
    if proc.returncode not in (0, 2):
        if stdout is not None:
            stdout = stdout.decode()
        if stderr is not None:
            stderr = stderr.decode()
        raise QuiltError(proc.returncode, stdout, stderr)
    if stdout is None:
        return ""
    return stdout


def quilt_pop_all(
        working_dir, patches_dir=None, series_file=None, quiet=None,
        force=False, refresh=False):
    """Pop all patches.

    Args:
      working_dir: Directory to work in
      patches_dir: Optional patches directory
      series_file: Optional series file
    """
    args = ["pop", "-a"]
    if force:
        args.append("-f")
    if refresh:
        args.append("--refresh")
    return run_quilt(
        args, working_dir=working_dir,
        patches_dir=patches_dir, series_file=series_file, quiet=quiet)


def quilt_pop(working_dir, patch, patches_dir=None, series_file=None, quiet=None):
    """Pop a patch.

    Args:
      working_dir: Directory to work in
      patch: Patch to apply
      patches_dir: Optional patches directory
      series_file: Optional series file
    """
    return run_quilt(
        ["pop", patch], working_dir=working_dir,
        patches_dir=patches_dir, series_file=series_file, quiet=quiet)


def quilt_push_all(working_dir, patches_dir=None, series_file=None, quiet=None,
                   force=False, refresh=False):
    """Push all patches.

    Args:
      working_dir: Directory to work in
      patches_dir: Optional patches directory
      series_file: Optional series file
    """
    args = ["push", "-a"]
    if force:
        args.append("-f")
    if refresh:
        args.append("--refresh")
    return run_quilt(
        args, working_dir=working_dir,
        patches_dir=patches_dir, series_file=series_file, quiet=quiet)


def quilt_push(working_dir, patch, patches_dir=None, series_file=None,
               quiet=None, force=False, refresh=False):
    """Push a patch.

    Args:
      working_dir: Directory to work in
      patch: Patch to push
      patches_dir: Optional patches directory
      series_file: Optional series file
      force: Force push
      refresh: Refresh
    """
    args = []
    if force:
        args.append("-f")
    if refresh:
        args.append("--refresh")
    return run_quilt(
        ["push", patch] + args, working_dir=working_dir,
        patches_dir=patches_dir, series_file=series_file, quiet=quiet)


def quilt_delete(working_dir, patch, patches_dir=None, series_file=None,
                 remove=False):
    """Delete a patch.

    Args:
      working_dir: Directory to work in
      patch: Patch to push
      patches_dir: Optional patches directory
      series_file: Optional series file
      remove: Remove the patch file as well
    """
    args = []
    if remove:
        args.append("-r")
    return run_quilt(
        ["delete", patch] + args, working_dir=working_dir,
        patches_dir=patches_dir, series_file=series_file)


def quilt_upgrade(working_dir):
    return run_quilt(["upgrade"], working_dir=working_dir)


def parse_quilt_applied(f):
    """Find the list of applied quilt patches.
    """
    return [os.fsdecode(patch.rstrip(b"\n"))
            for patch in f
            if patch.strip() != b""]


def quilt_unapplied(working_dir, patches_dir=None, series_file=None):
    """Find the list of unapplied quilt patches.

    Args:
      working_dir: Directory to work in
      patches_dir: Optional patches directory
      series_file: Optional series file
    """
    working_dir = os.path.abspath(working_dir)
    if patches_dir is None:
        patches_dir = os.path.join(working_dir, DEFAULT_PATCHES_DIR)
    try:
        unapplied_patches = run_quilt(
            ["unapplied"],
            working_dir=working_dir, patches_dir=patches_dir,
            series_file=series_file).splitlines()
        patch_names = []
        for patch in unapplied_patches:
            patch = os.fsdecode(patch)
            patch_names.append(os.path.relpath(patch, patches_dir))
        return patch_names
    except QuiltError as e:
        if e.retcode == 1:
            return []
        raise


def parse_quilt_series(f):
    """Find the list of patches.
    """
    return [os.fsdecode(patch.rstrip(b"\n")) for patch in f
            if patch.strip() != b""]
