import os
from kofoto.common import symlinkOrCopyFile

class OutputEngine:
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


    def generateIndex(self):
        if self.env.verbose:
            self.env.out("Generating index page...\n")
        self.createIndex()


    def generateAlbum(self, album, paths):
        if self.env.verbose:
            self.env.out("Generating album page for %s...\n" % album.getTag())

        self.createAlbumBegin(album, paths)
        children = album.getChildren()

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
                    child_ref_html[key] = "%s-%s-%s.html" % (
                        album.getId(),
                        child.getId(),
                        size)
                    child_ref_img[key] = "%s/%s" % (
                        self.imagesdest,
                        os.path.basename(imgabsloc))
                    child_loc_html[key] = os.path.join(
                        self.dest,
                        child_ref_html[key])
                    child_loc_img[key] = os.path.join(
                        self.dest,
                        self.imagesdest,
                        os.path.basename(imgabsloc))
                    if not os.path.isfile(child_loc_img[key]):
                        symlinkOrCopyFile(imgabsloc, child_loc_img[key])

        for ix in range(len(children)):
            child = children[ix]
            if child.isAlbum():
                #
                # Album child.
                #

                # Add album child as an album entry.
                albumtag = child.getTag()
                self.createAlbumEntry(album, child, {
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
                self.createImageEntry(album, child, {
                    "defaulthtmlref": child_ref_html[hash, self.
                                                     env.defaultsize],
                    "number": ix + 1,
                    "thumbimgref": child_ref_img[hash,
                                                 self.env.thumbnailsize],
                    "title": title,
                    })

                self.createImageBegin(album, child)

                # Create HTML pages for children, one per size.
                for size in self.env.imagesizes:
                    # Find previous image.
                    jx = ix - 1
                    while jx >= 0 and children[jx].isAlbum():
                        jx -= 1
                    if jx < 0:
                        previoushtmlref = None
                        previousimgref = None
                    else:
                        prevhash = children[jx].getHash()
                        previoushtmlref = child_ref_html[prevhash, size]
                        previousimgref = child_ref_img[prevhash, self.env.thumbnailsize]

                    # Find next image.
                    jx = ix + 1
                    while jx <= len(children) - 1 and children[jx].isAlbum():
                        jx += 1
                    if jx > len(children) - 1:
                        nexthtmlref = None
                        nextimgref = None
                    else:
                        nexthash = children[jx].getHash()
                        nexthtmlref = child_ref_html[nexthash, size]
                        nextimgref = child_ref_img[nexthash, self.env.thumbnailsize]

                    # Other sizes.
                    sizehtmlrefs = []
                    for sz in self.env.imagesizes:
                        sizehtmlrefs.append((sz, child_ref_html[hash, sz]))

                    file = open(child_loc_html[hash, size], "w")
                    file.write(self.createImageSize(album, child, size, {
                        "description": child.getAttribute("description"),
                        "imageid": child.getId(),
                        "imgref": child_ref_img[hash, size],
                        "previoushtmlref": previoushtmlref,
                        "previousimgref": previousimgref,
                        "nexthtmlref": nexthtmlref,
                        "nextimgref": nextimgref,
                        "sizehtmlrefs": sizehtmlrefs,
                        "title": title,
                        }))
                    file.close()
                self.createImageEnd(album, child)
        albumtag = album.getTag()
        albumfilename = albumtag + ".html"
        file = open(os.path.join(self.dest, albumfilename), "w")
        file.write(self.createAlbumEnd(album, {
            "description": album.getAttribute("description"),
            "tag": albumtag,
            "title": album.getAttribute("title"),
            }))
        file.close()


    def generateImage(self, image):
        pass
