import os

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
<p>Other sizes: %(sizerefs)s</p>
<p>Image ID: %(imageid)s</p>
<p>Description: %(description)s</p>
<p>Attributes:</p>
<p>%(attributes)s</p>
</body>
</html>
"""

class OutputGenerator:
    def __init__(self, env, root, dest):
        self.env = env
        self.root = root
        self.dest = dest
        self.imagesdest = "images"

        try:
            os.mkdir(self.dest)
        except OSError:
            pass
        try:
            os.mkdir(os.path.join(self.dest, self.imagesdest))
        except OSError:
            pass
        if self.env.verbose:
            self.env.out("Generating index page...\n")
        title = root.getAttribute("title")
        file = open(os.path.join(self.dest, "index.html"), "w")
        file.write(index_template % {
            "filename": root.getTag() + ".html",
            "tag": root.getTag(),
            "title": root.getAttribute("title"),
            })
        file.close()


    def generateAlbum(self, album, paths):
        if self.env.verbose:
            self.env.out("Generating album page for %s...\n" % album.getTag())
        albumentries = []
        children = album.getChildren()

        #
        # Generate path texts.
        #
        ps = []
        for path in paths:
            els = []
            for node in path:
                els.append("""<a href="%(tag)s.html">%(title)s</a>""" % {
                    "tag": node.getTag(),
                    "title": node.getAttribute("title"),
                    })
            ps.append(" » ".join(els))
        albumpaths = "<br />\n".join(ps)

        #
        # Generate and remember different sizes for images in the album.
        #
        child_ref_html = {}
        child_ref_img = {}
        child_loc_html = {}
        child_loc_img = {}
        for child in children:
            if not child.isAlbum():
                if self.env.verbose:
                    self.env.out("Generating image %s sizes %s...\n" % (
                        child.getId(),
                        ", ".join([str(x) for x in self.env.imagesizes])))
                hash = child.getHash()
                for size in self.env.imagesizes:
                    key = (hash, size)
                    imgabsloc = self.env.imagecache.get(child, size)
                    child_ref_html[key] = "%s-%s.html" % (
                        os.path.basename(imgabsloc).split(".")[0],
                        album.getId())
                    child_ref_img[key] = "%s/%s" % (
                        self.imagesdest,
                        os.path.basename(imgabsloc))
                    child_loc_html[key] = os.path.join(
                        self.dest,
                        "%s-%s.html" % (os.path.basename(imgabsloc).split(".")[0],
                                        album.getId()))
                    child_loc_img[key] = os.path.join(
                        self.dest,
                        self.imagesdest,
                        os.path.basename(imgabsloc))
                    if not os.path.isfile(child_loc_img[key]):
                        try:
                            os.symlink(imgabsloc, child_loc_img[key])
                        except AttributeError:
                            import shutil
                            shutil.copy(imgabsloc, child_loc_img[key])

        for ix in range(len(children)):
            child = children[ix]
            if child.isAlbum():
                #
                # Album child.
                #

                # Add album child as an album entry.
                albumtag = child.getTag()
                albumentries.append(album_entry_template % {
                    "filename": albumtag + ".html",
                    "number": ix + 1,
                    "tag": albumtag,
                    "title": child.getAttribute("title"),
                    })
            else:
                #
                # Image child.
                #

                if self.env.verbose:
                    self.env.out("Generating image page for %s in album %s...\n" % (
                        child.getId(),
                        album.getTag()))

                # Add image child as an album entry.
                hash = child.getHash()
                title = child.getAttribute("title")
                albumentries.append(image_entry_template % {
                    "defaulthtmlref": child_ref_html[hash, self.
                                                     env.defaultsize],
                    "number": ix + 1,
                    "thumbimgref": child_ref_img[hash,
                                                 self.env.thumbnailsize],
                    "title": title,
                    })

                # Attributes.
                attributes = []
                attributesmap = child.getAttributeMap()
                attrnames = attributesmap.keys()
                attrnames.sort()
                for name in attrnames:
                    attributes.append("<b>%s</b>: %s" % (name, attributesmap[name]))
                attributetext = "<br />\n".join(attributes)

                # Create HTML pages for children, one per size.
                for size in self.env.imagesizes:
                    # Find previous image.
                    jx = ix - 1
                    while jx >= 0 and children[jx].isAlbum():
                        jx -= 1
                    if jx < 0:
                        previoustext = "Previous: None"
                    else:
                        prevhash = children[jx].getHash()
                        previoustext = '<a href="%s">Previous: <img src="%s"></a>' % (
                            child_ref_html[prevhash, size],
                            child_ref_img[prevhash, self.env.thumbnailsize])

                    # Find next image.
                    jx = ix + 1
                    while jx <= len(children) - 1 and children[jx].isAlbum():
                        jx += 1
                    if jx > len(children) - 1:
                        nexttext = "Next: None"
                    else:
                        prevhash = children[jx].getHash()
                        nexttext = '<a href="%s">Next: <img src="%s"></a>' % (
                            child_ref_html[prevhash, size],
                            child_ref_img[prevhash, self.env.thumbnailsize])

                    # Other sizes.
                    sizerefs = []
                    for sz in self.env.imagesizes:
                        if sz != size:
                            sizerefs.append('<a href="%s">%s</a>' % (
                                child_ref_html[hash, sz],
                                sz))
                        else:
                            sizerefs.append("%s" % sz)
                    sizereftext = ", ".join(sizerefs)

                    file = open(child_loc_html[hash, size], "w")
                    file.write(image_template % {
                        "attributes": attributetext,
                        "description": child.getAttribute("description"),
                        "imageid": child.getId(),
                        "imgref": child_ref_img[hash, size],
                        "next": nexttext,
                        "previous": previoustext,
                        "sizerefs": sizereftext,
                        "title": title,
                        })
                    file.close()
        albumtag = album.getTag()
        albumfilename = albumtag + ".html"
        file = open(os.path.join(self.dest, albumfilename), "w")
        file.write(album_template % {
            "entries": "".join(albumentries),
            "description": album.getAttribute("description"),
            "paths": albumpaths,
            "tag": albumtag,
            "title": album.getAttribute("title"),
            })
        file.close()


    def generateImage(self, image):
        pass
