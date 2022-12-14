use Page

import os
import sys
from kofoto.clientenvironment import *
from kofoto.common import *
from kofoto.config import *
from kofoto.imagecache import *
from kofoto.search import *
from kofoto.shelf import *

def initServer():
    global env
    env = ClientEnvironment()
    env.setup()
    env.shelf.begin()
    if len(sys.argv) > 1:
        env.root = env.shelf.getAlbumByTag(unicode(sys.argv[1]))
    else:
        env.root = env.shelf.getRootAlbum()

def initNonStaticResponse():
    if request.path == "image":
        response.headerMap["content-type"] = "image/jpeg"
    else:
        response.headerMap["content-type"] = "application/xhtml+xml"

CherryClass Root(Page):
view:
    def index(self):
        return self.mainFrameset()

mask:
    def mainFrameset(self):
        <py-eval="self.header(frameset=True)">
        <frameset cols="30%, *">
        <frame name="treeframe" src="treeframe" />
        <frame name="contentframe" src="contentframe" />
        <noframes>
        This page needs frames. Sorry.
        </noframes>
        </frameset>
        <py-eval="self.footer(frameset=True)">

    def treeframe(self):
        <py-eval="self.header()">
        <ul>
        <py-eval="self.albumTreeHelper(env.root, 0, [])">
        </ul>
        <py-eval="self.footer()">

    def contentframe(self):
        <py-eval="self.header()">
        <p>Welcome to Kofoto.</p>
        <py-eval="self.footer()">

    def album(self, albumid):
        <py-eval="self.header()">
        <form method="post" action="/submitAlbum">
        <input type="hidden" name="origin" value="<py-eval="request.browserUrl">" />
        <input type="submit" value="Save" />
        <table>
        <py-exec="images = [x for x in env.shelf.getAlbum(unicode(albumid)).getChildren() if not x.isAlbum()]">
        <py-for="image in images">
        <py-exec="description = image.getAttribute(u'description') or u''">
        <tr>
        <td>
          <img src="/image?imageid=<py-eval="image.getId()">&amp;widthlimit=128&amp;heightlimit=128" />
        </td>
        <td>
        <textarea cols="40" rows="3" name="description-<py-eval="image.getId()">"><py-eval="description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').encode('utf8')"></textarea>
        </td>
        </tr>
        </py-for>
        </table>
        <input type="submit" value="Save" />
        </form>
        <py-eval="self.footer()">

view:
    def image(self, imageid, widthlimit, heightlimit):
        path, width, height = env.imageCache.get(
            env.shelf.getImage(int(imageid)).getPrimaryVersion(),
            int(widthlimit), int(heightlimit))
        return file(path).read()

    def submitAlbum(self, **kw):
        response.headerMap["status"] = 303
        response.headerMap["location"] = kw["origin"]
        for key, value in kw.items():
            if key.startswith("description-"):
                objectid = int(key.split("-")[1])
                object = env.shelf.getObject(objectid)
                object.setAttribute(u"description", value.decode("utf-8"))
        env.shelf.commit()
        env.shelf.begin()
        return ""

function:
    def albumTreeHelper(self, album, level, visited):
        tag = album.getTag().encode("utf8")
        x = album.getAttribute(u"title")
        if x:
            title = x.encode("utf8")
        else:
            title = tag
        ret = []
        indent = " " * (level + 1)
        oddeven = ["odd", "even"][level % 2]
        ret.append(
            "%s<li class=\"%s\"><a href=\"/album?albumid=%d\" target=\"contentframe\">%s</a>" % (
                indent,
                oddeven,
                album.getId(),
                title))
        if tag in visited:
            ret.append("\n%s<ul><li class=\"%s\">...</li></ul>\n" % (
                indent, oddeven))
        else:
            children = list(album.getAlbumChildren())
            if children:
                ret.append("\n%s <ul>\n" % indent)
                for child in children:
                    ret.append(self.albumTreeHelper(
                        child, level + 1, visited + [tag]))
                ret.append("%s </ul>\n" % indent)
                ret.append(indent)
        ret.append("</li>\n")
        return "".join(ret)
