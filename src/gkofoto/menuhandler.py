import gtk

class MenuGroup:
    def __init__(self, label=""):
        self.__label = label
        self.__childItems = []
        self.__childItemsMap = {}
        self.__radioGroup = None

    def addMenuItem(self, label, callback, callbackData=None):
        item = gtk.MenuItem(label)
        self.__addItem(item, label, callback, callbackData)

    def addStockImageMenuItem(self, label, stockId, callback,
                              callbackData=None):
        item = gtk.ImageMenuItem(label)
        image = gtk.Image()
        image.set_from_stock(stockId, gtk.ICON_SIZE_MENU)
        item.set_image(image)
        self.__addItem(item, label, callback, callbackData)

    def addImageMenuItem(self, label, imageFilename, callback,
                         callbackData=None):
        item = gtk.ImageMenuItem(label)
        image = gtk.Image()
        image.set_from_file(imageFilename)
        item.set_image(image)
        self.__addItem(item, label, callback, callbackData)

    def addCheckedMenuItem(self, label, callback, callbackData=None):
        item = gtk.CheckMenuItem(label)
        self.__addItem(item, label, callback, callbackData)

    def addRadioMenuItem(self, label, callback, callbackData=None):
        item = gtk.RadioMenuItem(self.__radioGroup, label)
        self.__addItem(item, label, callback, callbackData)
        self.__radioGroup = item

    def addSeparator(self):
        separator = gtk.SeparatorMenuItem()
        self.__childItems.append(separator)
        separator.show()
        self.__radioGroup = None

    def __getitem__(self, key):
        return self.__childItemsMap[key]

    def createGroupMenu(self):
        menu = gtk.Menu()
        for item in self:
            menu.append(item)
        menu.show()
        return menu

    def createGroupMenuItem(self):
        menuItem = gtk.MenuItem(self.__label)
        subMenu = self.createGroupMenu()
        if len(self) > 0:
            menuItem.set_submenu(subMenu)
        else:
            menuItem.set_sensitive(False)
        menuItem.show()
        return menuItem

    def __len__(self):
        return len(self.__childItems)

    def __iter__(self):
        for child in self.__childItems:
            yield child

    def enable(self):
        for child in self.__childItems:
            child.set_sensitive(True)

    def disable(self):
        for child in self.__childItems:
            child.set_sensitive(False)

    def __addItem(self, item, label, callback, callbackData=None):
        if callbackData == None:
            key = label
        else:
            key = callbackData
        self.__childItemsMap[key] = item
        self.__childItems.append(item)
        item.connect("activate", callback, callbackData)
        item.show()
