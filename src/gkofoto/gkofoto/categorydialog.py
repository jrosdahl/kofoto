import gtk
import string
import re
from environment import env
from gkofoto.taganddescriptiondialog import *

class CategoryDialog(TagAndDescriptionDialog):
    def __init__(self, title, categoryId=None):
        if categoryId:
            self._category = env.shelf.getCategory(categoryId)
            tagText = self._category.getTag()
            descText = self._category.getDescription()
        else:
            self._category = None
            tagText = u""
            descText = u""
        TagAndDescriptionDialog.__init__(self, title, tagText, descText)

    def _isTagOkay(self, tagString):
        try:
           # Check that the tag name is valid.
           verifyValidCategoryTag(tagString)
        except BadCategoryTagError:
            return False
        try:
            category = env.shelf.getCategoryByTag(tagString)
            if category == self._category:
                # The tag exists, but is same as before.
                return True
            else:
                # The tag is taken by another category.
                return False
        except CategoryDoesNotExistError:
            # The tag didn't exist.
            return True
