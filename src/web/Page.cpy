CherryClass Page:
mask:
    def header(self, frameset=False):
        <?xml version="1.0" encoding="utf-8"?>
        <!DOCTYPE html
            PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-<py-eval="frameset and 'frameset' or 'strict'">.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head>
        <link rel="stylesheet" href="/static/webkofoto.css" type="text/css" />
        </head>
        <py-if="not frameset"><body></py-if>

    def footer(self, frameset=False):
        <py-if="not frameset"></body></py-if>
        </html>
