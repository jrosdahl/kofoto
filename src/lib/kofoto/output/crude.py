import os
from kofoto.outputengine import OutputEngine
from kofoto.common import symlinkOrCopyFile

index_template = """<!DOCTYPE html
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head><title>Index page</title></head>
<body>
<h1>Index page</h1>
<p><a href="%(filename)s">%(title)s (%(tag)s)</a></p>
</body>
</html>
"""

album_template = """<!DOCTYPE html
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head><title>%(title)s (%(tag)s)</title></head>
<body>
<h1>%(title)s (%(tag)s)</h1>
<p>%(paths)s</p>
<p>Description: %(description)s</p>
<p>%(entries)s</p>
</body>
</html>
"""

album_entry_template = """
<p>
%(number)s. Album: <a href="%(filename)s">%(title)s</a> (%(tag)s)
</p>
"""

image_entry_template = """
<p>
%(number)s. <a href="%(defaulthtmlref)s"><img src="%(thumbimgref)s" /> %(title)s</a>
</p>
"""

image_template = """<!DOCTYPE html
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head><title>%(title)s</title></head>
<body>
<p>%(previous)s %(next)s</p>
<p><img src="%(imgref)s" /></p>
<p>Image sizes: %(sizerefs)s</p>
<p>Image ID: %(imageid)s</p>
<p>Description: %(description)s</p>
<p>Attributes:</p>
<p>%(attributes)s</p>
</body>
</html>
"""

class OutputGenerator(OutputEngine):
    def __init__(self, env, root, dest):
        OutputEngine.__init__(self, env, root, dest)


    def createIndex(self):
        symlinkOrCopyFile(
            "%s.html" % self.root.getTag(),
            os.path.join(self.dest, "index.html"))


    def createAlbumBegin(self, album, paths):
        ps = []
        for path in paths:
            els = []
            for node in path:
                els.append("""<a href="%(tag)s.html">%(title)s</a>""" % {
                    "tag": node.getTag(),
                    "title": node.getAttribute("title"),
                    })
            ps.append(" » ".join(els))
        self.albumpathtext = "<br />\n".join(ps)
        self.albumentries = []


    def createAlbumEntry(self, palbum, album, info):
        self.albumentries.append(album_entry_template % info)


    def createImageEntry(self, palbum, album, info):
        self.albumentries.append(image_entry_template % info)


    def createAlbumEnd(self, album, info):
        extrainfo = {
            "entries": "".join(self.albumentries),
            "paths": self.albumpathtext
            }
        info.update(extrainfo)
        if not info["description"]:
            info["description"] = info["title"]
        return album_template % info


    def createImageBegin(self, album, image):
        # Attributes.
        attributes = []
        attributesmap = image.getAttributeMap()
        attrnames = attributesmap.keys()
        attrnames.sort()
        for name in attrnames:
            attributes.append("<b>%s</b>: %s" % (name, attributesmap[name]))
        self.attributetext = "<br />\n".join(attributes)



    def createImageSize(self, album, image, size, info):
        if info["previousimgref"]:
            previoustext = '<a href="%s">Previous: <img src="%s"></a>' % (
                info["previoushtmlref"],
                info["previousimgref"])
        else:
            previoustext = "Previous: None"
        if info["nextimgref"]:
            nexttext = '<a href="%s">Next: <img src="%s"></a>' % (
                info["nexthtmlref"],
                info["nextimgref"])
        else:
            nexttext = "Next: None"

        sizerefs = []
        for sz, ref in info["sizehtmlrefs"]:
            if sz != size:
                sizerefs.append('<a href="%s">%s</a>' % (ref, sz))
            else:
                sizerefs.append("<b>%s</b>" % sz)
        sizereftext = ", ".join(sizerefs)

        extrainfo = {
            "attributes": self.attributetext,
            "next": nexttext,
            "previous": previoustext,
            "sizerefs": sizereftext,
            }
        info.update(extrainfo)
        if not info["description"]:
            info["description"] = info["title"]
        return image_template % info


    def createImageEnd(self, album, image):
        pass
