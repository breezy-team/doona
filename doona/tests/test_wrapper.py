#    Copyright (C) 2011 Canonical Ltd
#    Copyright (C) 2019-2021 Jelmer Vernooij <jelmer@jelmer.uk>
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

"""Tests for the quilt code."""

import os
import shutil
import tempfile

from doona.wrapper import (
    quilt_delete,
    quilt_pop_all,
    parse_quilt_applied,
    quilt_unapplied,
    quilt_push_all,
    parse_quilt_series,
    )

from unittest import TestCase

TRIVIAL_PATCH = """--- /dev/null	2012-01-02 01:09:10.986490031 +0100
+++ base/a	2012-01-02 20:03:59.710666215 +0100
@@ -0,0 +1 @@
+a
"""

class QuiltTests(TestCase):

    def setUp(self):
        super(QuiltTests, self).setUp()
        td = tempfile.mkdtemp()
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(td)
        self.addCleanup(shutil.rmtree, td)

    def make_empty_quilt_dir(self, path):
        os.mkdir(path)
        os.mkdir(os.path.join(path, 'patches/'))
        with open(os.path.join(path, "patches/series"), 'w') as f:
            f.write("\n")

    def build_tree_contents(self, contents):
        for e in contents:
            if e[0].endswith('/'):
                os.mkdir(e[0])
            else:
                with open(e[0], 'w') as f:
                    f.write(e[1])

    def test_series_all_empty(self):
        self.make_empty_quilt_dir("source")
        with open('source/patches/series', 'rb') as f:
            self.assertEqual([], parse_quilt_series(f))

    def test_series_all(self):
        self.make_empty_quilt_dir("source")
        self.build_tree_contents([
            ("source/patches/series", "patch1.diff\n"),
            ("source/patches/patch1.diff", TRIVIAL_PATCH)])
        with open('source/patches/series', 'rb') as f:
            self.assertEqual(["patch1.diff"], parse_quilt_series(f))

    def test_push_all_empty(self):
        self.make_empty_quilt_dir("source")
        quilt_push_all("source", quiet=True)

    def test_pop_all_empty(self):
        self.make_empty_quilt_dir("source")
        quilt_pop_all("source", quiet=True)

    def test_applied_empty(self):
        self.make_empty_quilt_dir("source")
        self.build_tree_contents([
            ("source/patches/series", "patch1.diff\n"),
            ("source/patches/patch1.diff", "foob ar")])
        self.assertFalse(os.path.exists('.pc/applied-patches'))

    def test_unapplied(self):
        self.make_empty_quilt_dir("source")
        self.build_tree_contents([
            ("source/patches/series", "patch1.diff\n"),
            ("source/patches/patch1.diff", "foob ar")])
        self.assertEqual(["patch1.diff"], quilt_unapplied("source"))

    def test_unapplied_dir(self):
        self.make_empty_quilt_dir("source")
        self.build_tree_contents([
            ("source/patches/series", "debian/patch1.diff\n"),
            ("source/patches/debian/", ),
            ("source/patches/debian/patch1.diff", "foob ar")])
        self.assertEqual(["debian/patch1.diff"], quilt_unapplied("source"))

    def test_unapplied_multi(self):
        self.make_empty_quilt_dir("source")
        self.build_tree_contents([
            ("source/patches/series", "patch1.diff\npatch2.diff"),
            ("source/patches/patch1.diff", "foob ar"),
            ("source/patches/patch2.diff", "bazb ar")])
        self.assertEqual(["patch1.diff", "patch2.diff"],
                          quilt_unapplied("source", "patches"))

    def test_delete(self):
        self.make_empty_quilt_dir("source")
        self.build_tree_contents([
            ("source/patches/series", "patch1.diff\npatch2.diff"),
            ("source/patches/patch1.diff", "foob ar"),
            ("source/patches/patch2.diff", "bazb ar")])
        quilt_delete("source", "patch1.diff", "patches", remove=False)
        with open('source/patches/series', 'rb') as f:
            self.assertEqual(['patch2.diff'], parse_quilt_series(f))
        quilt_delete("source", "patch2.diff", "patches", remove=True)
        self.assertTrue(os.path.exists('source/patches/patch1.diff'))
        self.assertFalse(os.path.exists('source/patches/patch2.diff'))
        with open('source/patches/series', 'rb') as f:
            self.assertEqual([], parse_quilt_series(f))
