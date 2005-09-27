from kofoto.gkofoto.environment import env
from kofoto.gkofoto.taganddescriptiondialog import TagAndDescriptionDialog
from kofoto.shelf import \
    AlbumDoesNotExistError, BadAlbumTagError, verifyValidAlbumTag

class AlbumDialog(TagAndDescriptionDialog):
    def __init__(self, title, albumId=None):
        if albumId is not None:
            self._album = env.shelf.getAlbum(albumId)
            tagText = self._album.getTag()
            descText = self._album.getAttribute(u"title")
            if descText == None:
                descText = u""
        else:
            self._album = None
            tagText = u""
            descText = u""
        TagAndDescriptionDialog.__init__(self, title, tagText, descText)
        label = self._widgets.get_widget("titleLabel")
        label.set_label(u"Title:")

    def _isTagOkay(self, tagString):
        try:
            # Check that the tag name is valid.
            verifyValidAlbumTag(tagString)
        except BadAlbumTagError:
            return False
        try:
            album = env.shelf.getAlbumByTag(tagString)
            if album == self._album:
                # The tag exists, but is same as before.
                return True
            else:
                # The tag is taken by another album.
                return False
        except AlbumDoesNotExistError:
            # The tag didn't exist.
            return True
