import sys
import gtk
from kofoto.shelf import ShelfLockedError
from gkofoto.mainwindow import MainWindow
from gkofoto.environment import env

class Controller:
    def __init__(self):
        self.__clipboard = None

    def start(self, setupOk):
        if setupOk:
            try:
                env.shelf.begin()
            except ShelfLockedError, e:
                env.startupNotices += [
                    "Error: Could not open shelf \"%s\"." % e +
                    " Another process is locking it.\n"]
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
            else:
                # Doesn't work with gtk.main_quit(). Don't know why.
                dialog.connect("response", lambda *x: sys.exit(1))
            dialog.run()
        if setupOk:
            self.__mainWindow = MainWindow()
            env.widgets["mainWindow"].connect("destroy", self.quit, False)
            env.widgets["mainWindow"].show()
        gtk.main()

    def quit(self, app, cancelButton=True):
        if env.shelf.isModified():
            widgets = gtk.glade.XML(env.gladeFile, "quitDialog")
            quitDialog = widgets.get_widget("quitDialog")
            if not cancelButton:
                widgets.get_widget("cancel").set_sensitive(False)
            result = quitDialog.run()
            if result == 0:
                env.shelf.commit()
                gtk.main_quit()
            elif result == 1:
                env.shelf.rollback()
                gtk.main_quit()
            else:
                quitDialog.destroy()
                return
        else:
            env.shelf.rollback()
            gtk.main_quit()

    def save(self, app):
        env.shelf.commit()
        env.shelf.begin()

    def revert(self, app):
        dialog = gtk.MessageDialog(
            type=gtk.MESSAGE_QUESTION,
            buttons=gtk.BUTTONS_YES_NO,
            message_format="Revert to the previously saved state and lose all changes?")
        if dialog.run() == gtk.RESPONSE_YES:
            env.shelf.rollback()
            env.shelf.begin()
            self.__mainWindow.reload()
        dialog.destroy()
