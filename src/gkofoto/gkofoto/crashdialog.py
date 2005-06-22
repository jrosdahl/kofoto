import pygtk
import gtk
import pango
import linecache
import os
import traceback
import re

class CrashDialog(gtk.Dialog):
    def __init__(self, exctype, value, tb, parent=None):
        gtk.Dialog.__init__(
            self, "GKofoto crash", parent,
            gtk.DIALOG_MODAL | gtk.DIALOG_NO_SEPARATOR,
            (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self._exctype = exctype
        self._value = value
        self._tb = tb

        self.set_default_size(
            gtk.gdk.screen_width() / 2,
            gtk.gdk.screen_height() / 2)
        self.set_border_width(10)

        self.vbox.set_spacing(5)

        button = gtk.Button(stock=gtk.STOCK_SAVE)
        button.show()
        button.connect("clicked", self._save)
        self.action_area.pack_start(button)
        self.action_area.reorder_child(button, 0)

        label = gtk.Label()
        label.set_markup(
            "<big><b>A programming error has been detected during the "
            "execution of this program.</b></big>\n\n"
            "Please report this problem at "
            "<span font_family='monospace' foreground='blue'>"
            "http://kofoto.rosdahl.net</span> "
            "or <span font_family='monospace' foreground='blue'>"
            "kofoto@rosdahl.net</span>\n"
            "and include the information below along with a description of "
            "what you did before the crash.")
        label.set_selectable(True)
        label.show()
        self.vbox.pack_start(label, False, False)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.show()
        self.vbox.pack_start(sw)

        self._textbuffer = gtk.TextBuffer()
        self._textbuffer.create_tag("filename", style=pango.STYLE_ITALIC)
        self._textbuffer.create_tag("name", weight=pango.WEIGHT_BOLD)
        self._textbuffer.create_tag("lineno", weight=pango.WEIGHT_BOLD)
        self._textbuffer.create_tag("exception", weight=pango.WEIGHT_BOLD)
        self._textbuffer.create_tag("source", family="monospace")

        self._formatTraceback(self._textbuffer, exctype, value, tb)

        textview = gtk.TextView(self._textbuffer)
        textview.set_editable(False)
        textview.set_cursor_visible(False)
        sw.add(textview)
        textview.show()

    def _save(self, widget):
        filechooser = gtk.FileChooserDialog(
            "Save crash log",
            self,
            gtk.FILE_CHOOSER_ACTION_SAVE,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
             gtk.STOCK_OK, gtk.RESPONSE_OK))
        if filechooser.run() == gtk.RESPONSE_OK:
            try:
                f = open(filechooser.get_filename(), "w")
                traceback.print_exception(
                    self._exctype, self._value, self._tb, None, f)
                f.close()
            except (OSError, IOError):
                dialog = gtk.MessageDialog(
                    self,
                    gtk.DIALOG_MODAL,
                    gtk.MESSAGE_ERROR,
                    gtk.BUTTONS_OK,
                    "Could not write to selected file.")
                dialog.run()
                dialog.destroy()
        filechooser.destroy()

    def _formatTraceback(self, textbuffer, exctype, value, tb):
        def add(line, *tags):
            textbuffer.insert_with_tags_by_name(
                textbuffer.get_end_iter(),
                line,
                *tags)
        def addFile(filename, lineno, name=None):
            add("  File ")
            add(filename, "filename")
            add(", line ")
            add(str(lineno), "lineno")
            if name:
                add(", in ")
                add(name, "name")
            add("\n")
        def addSource(line):
            add("  %s" % line.lstrip(), "source")

        cwd = os.getcwd()
        add("Traceback (most recent call last):\n")
        while tb is not None:
            lineno = tb.tb_lineno
            filename = tb.tb_frame.f_code.co_filename
            name = tb.tb_frame.f_code.co_name
            if filename.startswith(cwd):
                filename = filename[len(cwd) + 1:]
            addFile(filename, lineno, name)
            line = linecache.getline(filename, lineno)
            if line:
                addSource(line)
            tb = tb.tb_next
        lines = traceback.format_exception_only(exctype, value)
        for line in lines[:-1]:
            m = re.match("^  File \"([^\"]+)\", line (\d+)", line)
            if m:
                addFile(m.group(1), m.group(2))
            else:
                addSource(line)
        a = lines[-1].split(":")
        if len(a) == 1:
            add(a[0], "exception")
        else:
            add(a[0], "exception")
            add(":" + a[1])

def show(exctype, value, tb):
    window = CrashDialog(exctype, value, tb)
    window.run()
    window.destroy()
    raise SystemExit
