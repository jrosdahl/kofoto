# -*- python -*-

CherryClass Page:
aspect:
    (True) start:
        _page.append("<html><body>I'm the header<br><br>")
    (True) end:
        _page.append("<br><br>I'm the footer</body></html>")

CherryClass Root(Page):
mask:
    def index(self):
        hej
