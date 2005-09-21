import gtk
import string
import re
from environment import env
from kofoto.shelf import *

class TagAndDescriptionDialog:
    def __init__(self, title, tagText=u"", descText=u""):
        env.assertUnicode(tagText)
        env.assertUnicode(descText)
        self._widgets = gtk.glade.XML(env.gladeFile, "tagAndDescriptionDialog")
        self._dialog = self._widgets.get_widget("tagAndDescriptionDialog")
        self._dialog.set_title(title)
        self._tagWidget = self._widgets.get_widget("tag")
        self._tagWidget.set_text(tagText)
        self._descWidget = self._widgets.get_widget("description")
        self._descWidget.set_text(descText)
        self._descWidget.connect("changed", self._descriptionChanged, self._tagWidget)
        okbutton = self._widgets.get_widget("okbutton")
        self._tagWidget.connect("changed", self._tagChanged, okbutton)
        self.__descText = descText
        okbutton.set_sensitive(self._isTagOkay(tagText))

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

    def __generateTagName(self, descText):
        env.assertUnicode(descText)
        return re.sub(r"(?u)\W", "", descText).lower()

    def __generateTagNameDeprecated1(self, descText):
        # An algoritm for generating tag names used in previous gkofoto
        # versions (2004-04-26 -- 2004-05-15). This algoritm
        # must always remove all swedish characters, regardles of LOCAL
        # or UNICODE setting, to be backward compatible with the old version.
        env.assertUnicode(descText)
        return re.sub("\W", "", descText)

    def __generateTagNameDeprecated2(self, descText):
        # An algoritm for generating tag names used in previous gkofoto
        # versions (< 2004-04-26)
        env.assertUnicode(descText)
        return string.translate(descText.encode(env.codeset),
                                string.maketrans("", ""),
                                string.whitespace)

    def _descriptionChanged(self, description, tag):
        newDescText = description.get_text().decode("utf-8")
        currentTagText = self._tagWidget.get_text()
        if (currentTagText == self.__generateTagName(self.__descText) or
            currentTagText == self.__generateTagNameDeprecated1(self.__descText) or
            currentTagText == self.__generateTagNameDeprecated2(self.__descText)):
            tag.set_text(self.__generateTagName(newDescText))
        self.__descText = newDescText

    def _tagChanged(self, tag, button):
        tagString = tag.get_text().decode("utf-8")
        button.set_sensitive(self._isTagOkay(tagString))
