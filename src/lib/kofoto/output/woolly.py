import os
from kofoto.outputengine import OutputEngine
from kofoto.common import symlinkOrCopyFile

css = '''
body {
    color: #000000;
    background: #dddddd;
    font-family: Verdana, Geneva, Arial, Helvetica, sans-serif;
    font-size: 10pt;
}

img {
    color: #000000; /* Netscape */
    border-color: #000000; /* IE */
    display: block;
    border-style: solid;
    border-width: 1px;
}

img.noborder {
    border-style: none;
    display: inline;
}

img.toc {
    margin-top: 0.3cm;
}

a.toc {
    display: block;
    align: center;
}

td.arrow {
    font-size: 9pt;
}

a:link {
    color: #24238e;
}

a:visited {
    color: #6b4789;
}

.textleft {
    padding-right: 10pt;
}

.header {
    font-size : 10pt;
    background: #c5c2c0;
    table-layout: fixed;
    border-style: solid;
    border-width: 1px;
    border-color: #000000;
}

.photographer {
    font-size: 9pt;
}

.footer {
    font-size : 9pt;
}

h1 {
    font-size : 15pt;
    margin-bottom: 10
}

h2 {
    font-size: 10pt;
}

td.info {
    background: #c5c2c0;
    border-style: solid;
    border-width: 1px;
    border-color: #000000;
}
'''

png1x1 = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\xdac````\x00\x00\x00\x05\x00\x01z\xa8WP\x00\x00\x00\x00IEND\xaeB`\x82"

album_template = '''<!DOCTYPE html
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head>
<link href="woolly.css" type="text/css" rel="stylesheet" />
<title>%(title)s</title>
</head>
<body>
<table cellpadding="3" width="85%%" align="center" cellspacing="0">
<tr><td class="header">%(paths)s</td></tr>
<tr>
<td>
<h1 class="title">%(title)s</h1>
%(description)s
</td>
</tr>
<tr>
<td align="center">
<table cellpadding="20">
%(subalbumentries)s
%(imageentries)s
</table>
</td>
</tr>
<tr>
<td class="footer" colspan="3">
<p>&nbsp;</p>
<hr>
<small>%(blurb)s</small>
</td>
</tr>
</table>
</body>
</html>
'''

thumbnails_frame_template = '''<!DOCTYPE html
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head>
<link rel="stylesheet" href="woolly.css" type="text/css" />
</head>
<body>
%(entries)s
</body>
</html>
'''

# At least Opera 6.12 behaves strange with "text-align: center;" in
# stylesheet, so use align="center" instead.
thumbnails_frame_entry_template = '''<a name="%(number)s"></a>
<a href="%(htmlref)s" class="toc" target="main">
<div align="center">
<img src="%(thumbimgref)s" class="toc" /></div>
</a>
'''

image_entry_template = '''<td align="left" valign="bottom">
<a href="%(frameref)s">
<img src="%(thumbimgref)s" />
</a>
</td>
'''

image_frameset_template = '''<!DOCTYPE html
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head>
<link rel="stylesheet" href="woolly.css" type="text/css" />
<title>%(albumtitle)s</title>
</head>
<frameset cols="100%%, 200">
<frame name="main" src="%(imageframeref)s" />
<frame name="toc" src="%(thumbnailsframeref)s#%(imagenumber)s" marginheight="20" />
<noframes>
This album needs frames. Sorry.
</noframes>
</frameset>
</html>
'''

image_frame_template = '''<!DOCTYPE html
     PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head>
<link href="woolly.css" type="text/css" rel="stylesheet" />
<title>%(title)s</title>
</head>
<body>
<table cellpadding="3" width="85%%" align="center" cellspacing="0">
<tr><td class="header">%(paths)s</td></tr>
<tr>
<td>

<table width="100%%">
<tr><td colspan="3">%(previous)s %(next)s %(smaller)s %(larger)s</td></tr>
<tr>
<td></td>
<td><img class="noborder" src="images/1x1.png" height="1" width="%(imgmaxwidth)s" /></td>
<td></td>
</tr>
<tr>
<td width="50%%"></td>
<td align="center"><img src="%(imgref)s" align="center" /></td>
<td width="50%%"></td>
</tr>
<tr><td></td><td class="info">%(description)s</td><td></td></tr>
<tr>
<td></td>
<td class="footer">
<p>&nbsp;</p>
<hr>
<small>%(blurb)s</small>
</td>
<td></td>
</tr>
</table>

</td>
</tr>
</table>
</body>
</html>
'''


class OutputGenerator(OutputEngine):
    def __init__(self, env):
        OutputEngine.__init__(self, env)
        self.env = env


    def generateIndex(self, root):
        symlinkOrCopyFile(
            "%s.html" % root.getTag(),
            os.path.join(self.dest, "index.html"))
        self.writeFile("woolly.css", css)
        self.writeFile(os.path.join(self.imagesdest, "1x1.png"), png1x1, 1)


    def generateAlbum(self, album, subalbums, images, paths):
        # ------------------------------------------------------------
        # Create album symlink to default size.
        # ------------------------------------------------------------

        self.symlinkFile(
            "%s-%s.html" % (album.getTag(), self.env.defaultsize),
            "%s.html" % album.getTag())

        # ------------------------------------------------------------
        # Create album overview pages, one per size.
        # ------------------------------------------------------------

        for size in self.env.imagesizes:
            # Create path text, used in top of the album overview.
            pathtextElements = []
            for path in paths:
                els = []
                for node in path:
                    els.append('''<a href="%(htmlref)s">%(title)s</a>''' % {
                        "htmlref": "%s-%s.html" % (node.getTag(), size),
                        "title": node.getAttribute("title"),
                        })
                pathtextElements.append(" » ".join(els))
            pathtext = "<br />\n".join(pathtextElements)

            # Create text for subalbum entries.
            if subalbums:
                subalbumElements = []
                for subalbum in subalbums:
                    subalbumElements.append(
                        '<a href="%s-%s.html">%s</a>' % (
                            subalbum.getTag(),
                            size,
                            subalbum.getAttribute("title")))
                subalbumtext = "<tr><td>Subalbums:</td><td>%s</td></tr>" % (
                    "<br />\n".join(subalbumElements))
            else:
                subalbumtext = ""

            # Create text for image entries.
            number = 0
            imagetextElements = ["<tr>\n"]
            for image in images:
                if number % 3 == 0:
                    imagetextElements.append("</tr>\n<tr>\n")
                imagetextElements.append(image_entry_template % {
                    "frameref": "%s-%s-%s-frame.html" % (album.getId(),
                                                         number,
                                                         size),
                    "thumbimgref": self.getImageReference(
                        image,
                        self.env.thumbnailsize),
                    })
                number += 1
            imagetextElements.append("</tr>\n")
            imagetext = "".join(imagetextElements)

            # Album overview.
            self.writeFile(
                "%s-%s.html" % (album.getTag(), size),
                album_template % {
                    "blurb": self.blurb,
                    "description": (album.getAttribute("description") or
                                    album.getAttribute("title")),
                    "imageentries": imagetext,
                    "paths": pathtext,
                    "subalbumentries": subalbumtext,
                    "title": album.getAttribute("title"),
                })

        # ------------------------------------------------------------
        # Create image thumbnails frame, one per size.
        # ------------------------------------------------------------

        for size in self.env.imagesizes:
            # Create text for image thumbnails frame.
            thumbnailsframeElements = []
            number = 0
            for image in images:
                thumbnailsframeElements.append(
                    thumbnails_frame_entry_template % {
                        "htmlref": "%s-%s-%s.html" % (
                            album.getId(),
                            number,
                            size),
                        "number": number,
                        "thumbimgref": self.getImageReference(
                            image,
                            self.env.thumbnailsize),
                        })
                number += 1
            thumbnailstext = "\n".join(thumbnailsframeElements)

            # Image thumbnails frame.
            self.writeFile(
                "%s-%s-thumbnails.html" % (album.getTag(), size),
                thumbnails_frame_template % {"entries": thumbnailstext})


    def generateImage(self, album, image, images, number, paths):
        # ------------------------------------------------------------
        # Create image frameset, one per size.
        # ------------------------------------------------------------

        for size in self.env.imagesizes:
            self.writeFile(
                "%s-%s-%s-frame.html" % (
                    album.getId(),
                    number,
                    size),
                image_frameset_template % {
                    "albumtitle": album.getAttribute("title"),
                    "imageframeref": "%s-%s-%s.html" % (
                        album.getId(),
                        number,
                        size),
                    "imagenumber": number,
                    "thumbnailsframeref": "%s-%s-thumbnails.html" % (
                        album.getTag(),
                        size),
                    })

        # ------------------------------------------------------------
        # Create image frame, one per size.
        # ------------------------------------------------------------

        for sizenumber in range(len(self.env.imagesizes)):
            size = self.env.imagesizes[sizenumber]

            # Create path text, used in top of the image frame.
            pathtextElements = []
            for path in paths:
                els = []
                for node in path:
                    els.append('''<a href="%(htmlref)s" target="_top">%(title)s</a>''' % {
                        "htmlref": "%s-%s.html" % (node.getTag(), size),
                        "title": node.getAttribute("title"),
                        })
                pathtextElements.append(" » ".join(els))
            pathtext = "<br />\n".join(pathtextElements)

            if number > 0:
                previoustext = '<a href="%(htmlref)s">Previous</a>' % {
                    "htmlref": "%s-%s-%s.html" % (
                        album.getId(),
                        number - 1,
                        size)}
            else:
                previoustext = "<i>Previous</i>"
            if number < len(images) - 1:
                nexttext = '<a href="%(htmlref)s">Next</a>' % {
                    "htmlref": "%s-%s-%s.html" % (
                        album.getId(),
                        number + 1,
                        size)}
            else:
                nexttext = "<i>Next</i>"

            if sizenumber > 0:
                smallertext = '<a href="%(htmlref)s" target="_top">Smaller</a>' % {
                    "htmlref": "%s-%s-%s-frame.html" % (
                        album.getId(),
                        number,
                        self.env.imagesizes[sizenumber - 1])}
            else:
                smallertext = "<i>Smaller</i>"

            if sizenumber < len(self.env.imagesizes) - 1:
                largertext = '<a href="%(htmlref)s" target="_top">Larger</a>' % {
                    "htmlref": "%s-%s-%s-frame.html" % (
                        album.getId(),
                        number,
                        self.env.imagesizes[sizenumber + 1])}
            else:
                largertext = "<i>Larger</i>"

            self.writeFile(
                "%s-%s-%s.html" % (
                    album.getId(),
                    number,
                    size),
                image_frame_template % {
                    "blurb": self.blurb,
                    "description": (image.getAttribute("description") or
                                    image.getAttribute("title")),
                    "imgmaxwidth": size,
                    "imgref": self.getImageReference(image, size),
                    "larger": largertext,
                    "next": nexttext,
                    "paths": pathtext,
                    "previous": previoustext,
                    "smaller": smallertext,
                    "title": image.getAttribute("title"),
                    })
