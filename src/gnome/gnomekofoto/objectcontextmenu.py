import gtk
import gobject
import gtk

from environment import env

class ObjectContextMenu(gtk.Menu):
    viewMenuItems = {}
    

    def __init__(self, objects, selectedObjects):
        gtk.Menu.__init__(self)

        self._unregisterItem = gtk.MenuItem("Unregister")
        self._unregisterItem.show()
        self._unregisterItem.connect("activate", objects.unregisterObjects, None)
        self.append(self._unregisterItem)

        self._rotateLeftItem = gtk.MenuItem("Rotate left")
        self._rotateLeftItem.show()
        self._rotateLeftItem.connect("activate", objects.rotate, 270)
        self.append(self._rotateLeftItem)
        
        self._rotateRightItem = gtk.MenuItem("Rotate right")
        self._rotateRightItem.show()
        self._rotateRightItem.connect("activate", objects.rotate, 90)
        self.append(self._rotateRightItem)

        self._tableViewGroup = None
        self.tableViewSortItem = gtk.MenuItem("Sort by")
        self._tableViewSortSubMenu = gtk.Menu()

        sortAscendingItem = gtk.RadioMenuItem(None, "Ascending")
        sortDescendingItem = gtk.RadioMenuItem(sortAscendingItem, "Descending")
        sortAscendingItem.connect("activate", objects.setSortOrder, gtk.SORT_ASCENDING)
        sortDescendingItem.connect("activate", objects.setSortOrder, gtk.SORT_DESCENDING)
        sortAscendingItem.activate()
        sortSeparator = gtk.SeparatorMenuItem()
        sortAscendingItem.show()
        sortDescendingItem.show()
        sortSeparator.show()
        self._tableViewSortSubMenu.append(sortAscendingItem)
        self._tableViewSortSubMenu.append(sortDescendingItem)
        self._tableViewSortSubMenu.append(sortSeparator)
        self.tableViewSortItem.set_submenu(self._tableViewSortSubMenu)
        self.tableViewSortItem.show()
        self.append(self.tableViewSortItem)

        self.tableViewViewItem = gtk.MenuItem("View")
        self._tableViewViewSubMenu = gtk.Menu()
        self.tableViewViewItem.set_submenu(self._tableViewViewSubMenu)
        self.tableViewViewItem.show()
        self.append(self.tableViewViewItem)

        self._objects = objects
        self._selectedObjects = selectedObjects
        self.updateContextMenu()

        
        
    def addTableViewColumn(self, name, modelColumn, widget):
        # Populate the sort menu
        sortItem = gtk.RadioMenuItem(self._tableViewGroup, name)
        sortItem.connect("activate", self._objects.sortByColumn, modelColumn)
        if self._tableViewGroup == None:
            self._tableViewGroup = sortItem
        sortItem.show()
        self._tableViewSortSubMenu.append(sortItem)
        if name == env.defaultSortColumn:
            sortItem.activate()
        # Populate the view menu
        viewItem = gtk.CheckMenuItem(name)
        viewItem.connect("toggled", self._columnToggled, widget)
        viewItem.show()
        self.viewMenuItems[name] = viewItem
        self._tableViewViewSubMenu.append(viewItem)
        if name in env.defaultTableViewColumns:
            viewItem.set_active(gtk.TRUE)
        else:
            viewItem.set_active(gtk.FALSE)
        self._columnToggled(viewItem, widget)

    def _columnToggled(self, checkMenuItem, widget):
        widget.set_visible(checkMenuItem.get_active())
        
    def updateContextMenu(self):
        if len(self._selectedObjects) == 0:
            self._unregisterItem.set_sensitive(gtk.FALSE)
            self._rotateLeftItem.set_sensitive(gtk.FALSE)
            self._rotateRightItem.set_sensitive(gtk.FALSE)
        else:
            self._unregisterItem.set_sensitive(gtk.TRUE)
            self._rotateLeftItem.set_sensitive(gtk.TRUE)
            self._rotateRightItem.set_sensitive(gtk.TRUE)
