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
    border-style: none;
    display: block;
}

img.thinborder {
    color: #000000; /* Netscape */
    border-color: #000000; /* IE */
    border-style: solid;
    border-width: 1px;
}

img.toc {
    color: #000000; /* Netscape */
    border-color: #000000; /* IE */
    border-style: solid;
    border-width: 1px;
    margin-top: 0.3cm;
}

.albottom {
    vertical-align: bottom;
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

transparent_1x1_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\xdac````\x00\x00\x00\x05\x00\x01z\xa8WP\x00\x00\x00\x00IEND\xaeB`\x82"

frame_bottom_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x11\x08\x06\x00\x00\x00\x1c\xc3\xc6\x12\x00\x00\x001IDATx\xda\x8d\xc9A\r\x000\x0c\x03\xb1S\x07\'$\x072*\x8abHGa\xfe\x1aI\xc6vH\xb2\x05P\xdd\xcd\x99\x99\x8b\xed\xfd\x8cE\x92\x01\xf4\x00#%(P\xc8\xc2\x05\'\x00\x00\x00\x00IEND\xaeB`\x82"

frame_bottomleft_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x0c\x00\x00\x00\x11\x08\x06\x00\x00\x00\xe9=M\xa2\x00\x00\x01\x1fIDATx\xda\x95\x921n\xc2@\x10E\xdf$\x16\xe3\xca\x1d\xdd\xbaa$$\x9c:\xd7H\xc9!h\xa1\xe6\x06n)9\x83\x8f\xc1\x01R\x11\x96&%=b\x91\x92I\x918\xb2\xc0(\xe4K\xa3\xd5\x8e\xf4\xf6k\xff\x8cL\xa7\xd3\xd7\xe5rYUU%\x001F\xe6\xf3y\x8a1\xbe\x03\x89\x0be\xdd\x8b\x88P\x96%u]kJ\xc9\xe8Qv\xd9PU\xcc\x0c@z\x01w\x07\xa0=\xffR\x96R\xf2\x18\xa3\xbb;\"\xbf\x8f\xcaM \xcf\xf3\xb8^\xaf\x19\x0c\x06\"\"\x9cN'=\x1c\x0e\xe5p8\xd4<\xcf\xaf\x00\xd9n\xb7v>\x9f\x15\x10wg\xbf\xdf\xdbj\xb5\xaag\xb3\x99\x8dF#\xe9\xb8~;\x8c\xc7\xe3\xd8m4M\x83\xaa&3c2\x99p\x05\\Z.\x16\x0b\x8a\xa2\xb8\x19\xc2\x15\xb0\xdb\xed\xdc\xcc<\xc6\xe8\xedl\xbaA\xf4\xa5a\xaaZ\x87\x10LU\xdb?\xa8\xaa\x96!\x04\xedsU\xc0\x80\nx\xfa\xa9\x173{k\x9a\xe63\xeb\x01\x12\x10{6 \x99\x19\x0f\xfcS\xf7\x02\xden\xc4\xe3\x9d@q<\x1e\x9f7\x9b\xcd\x87\xdc\t(\x10\x00\xfd\x02\xb3\xd4h/\"\xda\xec\xa7\x00\x00\x00\x00IEND\xaeB`\x82"

frame_bottomright_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x11\x00\x00\x00\x11\x08\x06\x00\x00\x00;mG\xfa\x00\x00\x00\xd2IDATx\xda\xa5\x931\n\x840\x10E\x7f\x96@\xbc\x84\x95\x9d\xb9\x8b\xa5\x17\xd9\xde\xc2\xde\xdb\x05\x1b\x89U\x0e\xb1c\x91\xbf\xcd\xba\xac\xacY\x8d;\x10Bf\xe0\xc1<\xf2\xd14\xcdc\x9a&\xc6\x18\x19c\xa4s\x8em\xdb\xd29w\xd4\x8b\xd6Z\x07\xc0\xde\x86a0eYB)\x85\xab\xa5\xab\xaa\xfa\x0b\x00\x00\x1a\x00Hb\xef>\r\x19\xc7\xf1\xfd \x89y\x9e!\"y\x90\xbe\xef7\x90eYP\x14\x05\x8c1\xe7!]\xd7}5\x8d1Xe\x9fYM\xd7u\xbd;\xc8\x91\xadS\x83\x1c\xd9\x1b\xb1)\xd8\x91\xec\x8d\xd8\x14\xe4H\xf6\xae\xd8\xbd\xfa%;)6G\xb6\xce\xf9T\x9f\x92\xd7\xb3\x8aenVH\xc2{O\x11!\x00\xaaW\x9c\xb3!\"\xc2\x10\x82\x17\x91\xbb\x02`/\x86\x97\x00\x04@x\x02\xb7\x89\xa5\xf8\x0b\xe9\xfe\xce\x00\x00\x00\x00IEND\xaeB`\x82"

frame_left_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x06\x00\x00\x00\x01\x08\x06\x00\x00\x00\xfd\xc9\xdf\xf0\x00\x00\x00\x1fIDATx\xda\x05\xc1\x01\x01\x00\x00\x08\xc20\xfb\xd0\x87\xe4\xcfs\xdc\xae-\x80\xea\xd4\x01&\xe1\x01\xe4\xbc\x12\x12\xcbp\xe9\x92\x00\x00\x00\x00IEND\xaeB`\x82"

frame_right_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x11\x00\x00\x00\x01\x08\x06\x00\x00\x008\xbbEa\x00\x00\x00(IDATx\xda\x85\xc8A\x01\x000\x10\xc20\xfc\xe0\xe7\x94WO\x99\x84\xe5\x99\xb4\x05P\x9d:`w7`\x9f\xb3-I\xfa\x00N\xd33\x8ef\xbf\xfbs\x00\x00\x00\x00IEND\xaeB`\x82"

frame_top_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x06\x08\x06\x00\x00\x00\x02\x10\xf41\x00\x00\x00$IDATx\xda\x05\xc1\x01\x11\x00\x00\x08\x02\xb1?\xeb\xd8\x87\xe4\x1cq\xd0\rI\xc6vi{\x030I\x8e\xdd\xf5\x03\xe1\xef\x0e$\xd4\n|5\x00\x00\x00\x00IEND\xaeB`\x82"

frame_topleft_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x06\x00\x00\x00\x06\x08\x06\x00\x00\x00\xe0\xcc\xefH\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\tpHYs\x00\x00\x0b\x12\x00\x00\x0b\x12\x01\xd2\xdd~\xfc\x00\x00\x00\x07tIME\x07\xd3\x05\x01\x0e3\x1b\\\xb2\xad\xe2\x00\x00\x00TIDATx\x9c]\x89\xb1\r\xc0 \x10\x03m\x84`\x0f\xbe\"\x03\xb1\x00#\xb0Xv\xfa%pE*\xa2\x90\x93\\\xf8\x8e\xad\xb5[\x92\xa5\x94H\x12\x9b8\xe7\xb4\xde\xfbUJ9C\xce\x99f\xc6Z\xeb\x11\xc2>$\xdf\x01@\xc4\x0fIpw\x84\xaf\\k\xc1\xdd1\xc6\xd0\x03E\xd4\x18G\xcb:X\x17\x00\x00\x00\x00IEND\xaeB`\x82"

frame_topright_png = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x11\x00\x00\x00\x0c\x08\x06\x00\x00\x00\x84%V\xbf\x00\x00\x01\x15IDATx\xda\x8d\x91\xb1j\x84@\x10\x86\xffM\xc4\x01S]awi\\-\xf4\xea\x80\xaf\x11H|\x81{\x04\xab4v\x96\xf7\x08\xf6\xd7\xddk\xa4?\xdb\x11$vW\xa4\x13f\xe1\xd84&\x98\x9c\x86\xfd\x9b\x85\x9f\xe1c\xe7\x1bU\x14E\x8b)\xd6Z\x18c,\x11q]\xd7e\x92$\x0c\x87xUUesH\xd7u\xb6i\x1a\x88\x08\xc11^\x96ej\x0eQJ\x81\x88\x14\x00\xe5\x0c\x01\x00\xa5n\xe7\xad\xb5\xae\x0c\xdc13D\xe4W)\"\xc4\xcc\xfat:\xed\xb4\xd6;\x00\x19\x00\r`q\xc5\xfb\xbe\xef\xdf\xf2<\xf76\x9b\r\x00\xe0r\xb9\xa8\xe3\xf1\xf8\xd0\xb6m~>\x9f\x9f\x8d1\xafA\x10\xbc\x8c\xe3\xf8t\xbd^\xdf\x01|\xde\xac\xc3\xcc\x1f\"\xa2\xe7\x0e\xc20\xa4\xfd~\xaf\xa3(\x02\x000\xb3-\xcb\x12\xccLkN\xe4oID\xd0Z\xab4M\xe7\xdd\xaalo\xa9\xfc\x16=\x7f\x97\xe4\xff\x0bY\tMr\x7f\x0e8m1\xb8B\x14\x11=\xc6q|\xf0}_\xa6\x0b\xdaa\x18XDJ\xe7\x9fl\xb7\xdbU\xd9_0\xf6t\x96\x1c\xda\xaaL\x00\x00\x00\x00IEND\xaeB`\x82"

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

# At least Opera 6.12 behaves strangely with "text-align: center;" in
# stylesheet, so use align="center" instead.
thumbnails_frame_entry_template = '''<a name="%(number)s"></a>
<a href="%(htmlref)s" class="toc" target="main">
<div align="center">
<img src="%(thumbimgref)s" class="toc" /></div>
</a>
'''

subalbum_entry_template = '''<td align="center" valign="top">
<p>%(title)s</p>
<table border="0" cellspacing="0" cellpadding="0">
<tr>
<td><img class="albottom" src="images/frame-topleft.png" /></td>
<td><img class="albottom" src="images/frame-top.png" width="6" height="6" /></td>
<td><img class="albottom" src="images/frame-top.png" width="%(thumbwidth_minus_6)s" height="6" /></td>
<td class="albottom" rowspan="2"><img class="albottom" src="images/frame-topright.png" /></td>
</tr>
<tr>
<td rowspan="2"><img class="albottom" src="images/frame-left.png" width="6" height="%(thumbheight)s" /></td>
<td rowspan="2" colspan="2"><a href="%(htmlref)s"><img class="albottom" src="%(thumbimgref)s" width="%(thumbwidth)s" height="%(thumbheight)s"/></a></td>
</tr>
<tr><td><img class="albottom" src="images/frame-right.png" width="17" height="%(thumbheight_minus_6)s" /></td></tr>
<tr>
<td colspan="2"><img class="albottom" src="images/frame-bottomleft.png" /></td>
<td><img class="albottom" src="images/frame-bottom.png" width="%(thumbwidth_minus_6)s" height="17" /></td>
<td><img class="albottom" src="images/frame-bottomright.png" /></td>
</tr>
</table>
</td>
'''

image_entry_template = '''<td align="left" valign="bottom">
<a href="%(frameref)s">
<img class="thinborder" src="%(thumbimgref)s" />
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
<td><img src="images/1x1.png" height="1" width="%(imgmaxwidth)s" /></td>
<td></td>
</tr>
<tr>
<td width="50%%"></td>
<td align="center"><img class="thinborder" src="%(imgref)s" align="center" /></td>
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
        for data, filename in [
                (transparent_1x1_png, "1x1.png"),
                (frame_bottom_png, "frame-bottom.png"),
                (frame_bottomleft_png, "frame-bottomleft.png"),
                (frame_bottomright_png, "frame-bottomright.png"),
                (frame_left_png, "frame-left.png"),
                (frame_right_png, "frame-right.png"),
                (frame_top_png, "frame-top.png"),
                (frame_topleft_png, "frame-topleft.png"),
                (frame_topright_png, "frame-topright.png")]:
            self.writeFile(
                os.path.join(self.imagesdest, filename), data, 1)


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
                number = 0
                subalbumtextElements = ["<tr>\n"]
                for subalbum in subalbums:
                    if number % 3 == 0:
                        subalbumtextElements.append("</tr>\n<tr>\n")

                    frontimage = self._getFrontImage(subalbum)
                    if frontimage:
                        thumbimgref = self.getImageReference(
                            frontimage, self.env.thumbnailsize)
                        thumbwidth, thumbheight = self.getLimitedSize(
                            frontimage, self.env.thumbnailsize)
                    else:
                        thumbimgref = os.path.join(self.imagesdest, "1x1.png")
                        thumbwidth = self.env.thumbnailsize
                        thumbheight = 3 * self.env.thumbnailsize / 4

                    subalbumtextElements.append(subalbum_entry_template % {
                        "htmlref": "%s-%s.html" % (subalbum.getTag(), size),
                        "thumbheight": thumbheight,
                        "thumbheight_minus_6": thumbheight - 6,
                        "thumbwidth": thumbwidth,
                        "thumbwidth_minus_6": thumbwidth - 6,
                        "thumbimgref": thumbimgref,
                        "title": subalbum.getAttribute("title"),
                        })
                    number += 1
                subalbumtextElements.append("</tr>\n")
                subalbumtext = "".join(subalbumtextElements)
            else:
                subalbumtext = ""

            # Create text for image entries.
            if images:
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
            else:
                imagetext = ""

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


    def _getFrontImage(self, object, visited=None):
        if visited and object.getId() in visited:
            return None

        if object.isAlbum():
            if not visited:
                visited = []
            visited.append(object.getId())
            thumbid = object.getAttribute("frontimage")
            if thumbid:
                from kofoto.shelf import ImageDoesNotExistError
                try:
                    return self.env.shelf.getImage(thumbid)
                except ImageDoesNotExistError:
                    pass
            children = object.getChildren()
            if children:
                return self._getFrontImage(children[0], visited)
            return None
        else:
            return object
