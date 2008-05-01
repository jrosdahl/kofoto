import gtk
import re
from kofoto.gkofoto.environment import env

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

    def _isTagOkay(self, tag):
        raise NotImplementedError

    def __generateTagName(self, descText):
        env.assertUnicode(descText)
        return re.sub(r"(?u)\W", "", descText).lower()

    def _descriptionChanged(self, description, tag):
        newDescText = description.get_text().decode("utf-8")
        currentTagText = self._tagWidget.get_text()
        if currentTagText == self.__generateTagName(self.__descText):
            tag.set_text(self.__generateTagName(newDescText))
        self.__descText = newDescText

    def _tagChanged(self, tag, button):
        tagString = tag.get_text().decode("utf-8")
        button.set_sensitive(self._isTagOkay(tagString))
