import gtk
import string
from environment import env
from kofoto.shelf import *

class CategoryDialog:
    def __init__(self, title, categoryId=None):
        if categoryId:
            category = env.shelf.getCategory(categoryId)
            tagText = category.getTag()
            descText = category.getDescription()
        else:
            tagText = ""
            descText = ""
            
        widgets = gtk.glade.XML(env.gladeFile, "categoryProperties")
        self._dialog = widgets.get_widget("categoryProperties")
        self._dialog.set_title(title)
        self._tagWidget = widgets.get_widget("tag")
        self._tagWidget.set_text(tagText)
        self._descWidget = widgets.get_widget("description")
        self._descWidget.set_text(descText)
        self._descWidget.connect("changed", self._descriptionChanged, self._tagWidget)
        self._tagWidget.connect("changed", self._tagChanged, widgets.get_widget("okbutton"))

    def run(self, ok=None, data=None):
        result = self._dialog.run()
        tag = self._tagWidget.get_text().decode("utf-8")
        desc = self._descWidget.get_text().decode("utf-8")            
        self._dialog.destroy()       
        if result == gtk.RESPONSE_OK:
            if ok == None:
                return None
            else:
                if data:
                    return ok(tag, desc, data)
                else:
                    return ok(tag, desc)
        else:
            return None
    
    def _descriptionChanged(self, description, tag):
        # Remove all whitespaces in description and then use it as tag
        tag.set_text(string.translate(description.get_text(),
                                      string.maketrans("", ""),
                                      string.whitespace))

    def _tagChanged(self, tag, button):
        tagString = tag.get_text().decode("utf-8")
        try:
           # Check that the tag name is valid
           verifyValidCategoryTag(tagString)
        except(BadCategoryTagError):
            button.set_sensitive(False)
            return
        try:
            # Make sure that the tag name is not already taken
            env.shelf.getCategory(tagString)
            button.set_sensitive(False)
        except(CategoryDoesNotExistError):
            button.set_sensitive(True)
