import gtk
import string
import re
from environment import env
from gnomekofoto.taganddescriptiondialog import *

class CategoryDialog(TagAndDescriptionDialog):
    def __init__(self, title, categoryId=None):
        if categoryId:
            category = env.shelf.getCategory(categoryId)
            tagText = category.getTag()
            descText = category.getDescription()
        else:
            tagText = u""
            descText = u""
        TagAndDescriptionDialog.__init__(self, title, tagText, descText)
            
    def _isTagValid(self, tagString):
        try:
           # Check that the tag name is valid
           verifyValidCategoryTag(tagString)
        except(BadCategoryTagError):
            return False
        try:
            # Make sure that the tag name is not already taken
            env.shelf.getCategory(tagString)
            return False
        except(CategoryDoesNotExistError):
            return True
