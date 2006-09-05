import os
import sys
import unittest

testModules = ["dagtests", "kofoto.iodict", "shelftests", "searchtests"]

cwd = os.getcwd()
libdir = unicode(os.path.realpath(
    os.path.join(os.path.dirname(sys.argv[0]), "..", "packages")))
os.chdir(libdir)
sys.path.insert(0, libdir)

def suite():
    alltests = unittest.TestSuite()
    for module in [__import__(x) for x in testModules]:
        alltests.addTest(unittest.findTestCases(module))
    return alltests

if __name__ == "__main__":
    unittest.main(defaultTest="suite")
