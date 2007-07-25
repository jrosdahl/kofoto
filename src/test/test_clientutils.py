#! /usr/bin/env python

import os
import sys
import unittest

if __name__ == "__main__":
    cwd = os.getcwd()
    libdir = unicode(os.path.realpath(
        os.path.join(os.path.dirname(sys.argv[0]), "..", "packages")))
    os.chdir(libdir)
    sys.path.insert(0, libdir)

from kofoto.clientutils import group_image_versions


class TestClientUtils(unittest.TestCase):
    def test_group_image_versions(self):
        transforms = [
            # Different bases.
            (["/foo/bar.jpg", "/foo/bar2.jpg"],
             [["/foo/bar.jpg"], ["/foo/bar2.jpg"]]),
            # Different directories.
            (["/foo/bar.jpg", "/foo2/bar.cr2"],
             [["/foo/bar.jpg"], ["/foo2/bar.cr2"]]),
            # Sort known original first.
            (["/foo/bar.jpg", "/foo/bar.cr2"],
             [["/foo/bar.cr2", "/foo/bar.jpg"]]),
            # Handle uppercase extensions.
            (["/foo/bar.JPG", "/foo/bar.CR2"],
             [["/foo/bar.CR2", "/foo/bar.JPG"]]),
            # Sort shorter filenames first.
            (["/foo/bar-test.jpg", "/foo/bar.jpg", "/foo/bar-fix.jpg"],
             [["/foo/bar.jpg", "/foo/bar-fix.jpg", "/foo/bar-test.jpg"]]),
            # Sort filenames with equal lengths conventionally.
            (["/foo/bar-test2.jpg", "/foo/bar.jpg", "/foo/bar-test1.jpg"],
             [["/foo/bar.jpg", "/foo/bar-test1.jpg", "/foo/bar-test2.jpg"]]),
            ]
        for (paths, expected) in transforms:
            actual = list(group_image_versions(paths))
            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
