"""Read-only support for files with embedded JPEG thumbnail in EXIF header."""

import Image
from PIL import JpegImagePlugin
from kofoto import EXIF
from cStringIO import StringIO

class ExifThumbImageFile(JpegImagePlugin.JpegImageFile):
    format = "EXIFTHUMB"
    format_description = "EXIF JPEG thumbnail"

    def _open(self):
        try:
            tags = EXIF.process_file(self.fp, details=False)
        except: # Work-around for buggy EXIF library.
            raise SyntaxError("not an EXIFTHUMB file")

        if "JPEGThumbnail" in tags:
            self.fp = StringIO(tags["JPEGThumbnail"])
        else:
            raise SyntaxError("not an EXIFTHUMB file")

        JpegImagePlugin.JpegImageFile._open(self)

Image.register_open("EXIFTHUMB", ExifThumbImageFile)

# Known extensions with embedded thumbnails:
Image.register_extension("CR2", ".cr2")
