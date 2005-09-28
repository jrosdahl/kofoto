import gtk
from kofoto.shelf import ShelfLockedError, UnsupportedShelfError
from kofoto.gkofoto.mainwindow import MainWindow
from kofoto.gkofoto.environment import env

class Controller:
    def __init__(self):
        self.__clipboard = None
        self.__mainWindow = None

    def start(self, setupOk):
        if setupOk:
            try:
                if env.shelf.isUpgradable():
                    dialog = gtk.MessageDialog(
                        type=gtk.MESSAGE_INFO,
                        buttons=gtk.BUTTONS_OK_CANCEL,
                        message_format=
                            "You have a metadata database from an older"
                            " Kofoto version. It needs to be upgraded"
                            " before you can continue.\n\n"
                            "Press OK to upgrade the database"
                            " automatically. A backup copy of the old"
                            " database will be made before upgrading.")
                    dialog.set_default_response(gtk.RESPONSE_OK)
                    result = dialog.run()
                    if result == gtk.RESPONSE_CANCEL:
                        return
                    dialog.set_response_sensitive(gtk.RESPONSE_CANCEL, False)
                    dialog.set_response_sensitive(gtk.RESPONSE_OK, False)
                    dialog.label.set_text("Upgrading database. Please wait...")
                    while gtk.events_pending():
                        gtk.main_iteration()
                    success = env.shelf.tryUpgrade()
                    dialog.destroy()
                    if not success:
                        dialog = gtk.MessageDialog(
                            type=gtk.MESSAGE_ERROR,
                            buttons=gtk.BUTTONS_OK,
                            message_format="Failed to upgrade metadata database format.\n")
                        dialog.run()
                        dialog.destroy()
                        return
                env.shelf.begin()
            except ShelfLockedError, e:
                env.startupNotices += [
                    "Error: Could not open metadata database \"%s\"." % e +
                    " Another process is locking it.\n"]
                setupOk = False
            except UnsupportedShelfError, e:
                env.startupNotices += [
                    "Error: Too new format for metadata database \"%s\"." % e]
                setupOk = False
        if env.startupNotices:
            if setupOk:
                dialogtype = gtk.MESSAGE_INFO
            else:
                dialogtype = gtk.MESSAGE_ERROR
            dialog = gtk.MessageDialog(
                type=dialogtype,
                buttons=gtk.BUTTONS_OK,
                message_format="".join(env.startupNotices))
            if setupOk:
                # Doesn't work with x[0].destroy(). Don't know why.
                dialog.connect("response", lambda *x: x[0].hide())
            dialog.run()
        if setupOk:
            self.__mainWindow = MainWindow()
            env.widgets["mainWindow"].connect("destroy", self.quit_cb, False)
            env.widgets["mainWindow"].show()
            gtk.main()

    def quit_cb(self, app, cancelButton=True):
        if env.shelf.isModified():
            widgets = gtk.glade.XML(env.gladeFile, "quitDialog")
            quitDialog = widgets.get_widget("quitDialog")
            if not cancelButton:
                widgets.get_widget("cancel").set_sensitive(False)
            result = quitDialog.run()
            if result == 0:
                env.shelf.commit()
                self._doQuit()
            elif result == 1:
                env.shelf.rollback()
                self._doQuit()
            else:
                quitDialog.destroy()
                return
        else:
            env.shelf.rollback()
            self._doQuit()

    def save_cb(self, app):
        env.shelf.commit()
        env.shelf.begin()

    def revert_cb(self, app):
        dialog = gtk.MessageDialog(
            type=gtk.MESSAGE_QUESTION,
            buttons=gtk.BUTTONS_YES_NO,
            message_format="Revert to the previously saved state and lose all changes?")
        if dialog.run() == gtk.RESPONSE_YES:
            env.shelf.rollback()
            env.shelf.begin()
            self.__mainWindow.reload()
        dialog.destroy()

    def _doQuit(self):
        self.__mainWindow.saveState()
        gtk.main_quit()
