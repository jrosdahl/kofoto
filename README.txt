 _  __      __       _
| |/ /___  / _| ___ | |_ ___
| ' // _ \| |_ / _ \| __/ _ \
| . \ (_) |  _| (_) | || (_) |
|_|\_\___/|_|  \___/ \__\___/


OVERVIEW
========

Kofoto is an open source tool for organizing and viewing digital
images, typically photographs from a digital camera. Both graphical
and command-line interfaces are available.

With Kofoto, you can:

    * Organize images by use of categories (AKA "tags").
    * Organize images in an album tree.
    * Associate images with attributes.
    * Search for images matching a search expression.
    * View images.
    * Rotate images.
    * Generate HTML pages of an album tree. 

Kofoto is currently a bit rough on the edges, yet functional. But
please go ahead and try it, if you like!


LICENSE
=======

See COPYING.txt. The license is a BSD-like open source license (see
http://www.opensource.org).


CONTACT
=======

Email: kofoto@rosdahl.net
Web page: http://kofoto.rosdahl.net


INSTALLATION
============

A. Unix
-------

   Prerequisites
   -------------

   Kofoto depends on the following third-party softwares:

     * Python 2.3 or newer. Found at:

           http://www.python.org

     * GTK+ 2.2. Found at:

           http://www.pygtk.org

     * Glade 2.0. Found at:

           http://glade.gnome.org

     * PyGTK for GTK+ 2.2 (including Glade bindings). Found at:

           http://www.gtk.org

     * Python Imaging Library. Found at:

           http://www.pythonware.com/products/pil/

     * PySQLite. Found at:

           http://pysqlite.sourceforge.net

   On a Debian GNU/Linux machine, installing the packages
   python-glade2, python-gtk2, python-imaging and python-sqlite should
   do.


   Installing and running Kofoto
   -----------------------------

   0. Install the prerequisites, if necessary.
   1. Unpack the kofoto-*.tar.gz archive.
   2. Run "python setup.py install" in the created directory to
      install Kofoto at the default location. See
      http://www.python.org/doc/current/inst/inst.html for more
      information.
   3. Run gkofoto or "kofoto --help".


B. Windows
----------

   Prerequisites
   -------------

   Kofoto depends on the following third-party softwares:

     * Python 2.3 or newer. Found at:

           http://www.python.org

     * GTK+ 2.2 (including Glade 2.0) for Windows. Found at:

            http://www.dropline.net/gtk/

     * PyGTK for GTK+ 2.2 (including Glade bindings) for Windows. Found at:

            http://www.mapr.ucl.ac.be/~gustin/win32_ports/pygtk.html

     * Python Imaging Library. Found at:

           http://www.pythonware.com/products/pil/

     * PySQLite. Found at:

           http://pysqlite.sourceforge.net


   Installing and running Kofoto
   -----------------------------

   0. Install the prerequisites, if necessary.
   1. Run the kofoto-*.win32.exe Windows installer and complete the
      wizard.
   2. Double-click the Kofoto shortcut at the desktop or in the start
      menu.


VERSION HISTORY
===============

0.2.2 (2004-10-01)

    Corrections:

      * Fixed a bug that made the image preloader leak lots of memory
        (ticket #68).

0.2.1 (2004-09-19)

    Corrections:

      * Handle missing image files gracefully in the image preloader
        (ticket #67).

0.2 (2004-09-19)

    Enhancements:

      * Preloading of images (ticket #28).
      * Load table view asynchronously (ticket #26).
      * Added search filter field (ticket #32).
      * Added status bar (ticket #58).
      * Added accelerators for next/previous image (ticket #60).

    Corrections:

      * Quote file arguments to the rotation commands correctly in the
        default configuration file.
      * Made woolly output valid XHTML Transitional (ticket #52).
        Patch from Erik Forsberg. Thanks!
      * Don't register identified MPEG files or images that PIL can't
        convert to RGB mode.
      * Made delete in the edit menu work (ticket #66).
      * Made destroy in the edit unselectable when the album tree
        loses focus.
      * Update the toggle column in the category tree after paste
        (ticket #45).
      * Make the "registered" attribute equal for all images when
        registering (ticket #41).
      * Fixed error when choosing "Properties..." for a selected album
        in the table view (ticket #49).
      * Ignore shift-related warnings from PIL (ticket #50).
      * Catch errors from buggy PIL plugins.
      * Fixed a bug that made the EXIF module unable to read some EXIF
        fields (ticket #64).
      * Implemented work-around for a problem with repeated view
        freezes (ticket #48).
      * Reload album tree when an album has been cut or pasted (ticket
        #65).
      * Added dependency on python-glade2 in the Debian package. Noted
        by Erik Forsberg.
      * Added dependency on libjpeg-progs in the Debian package
        (ticket #63). Noted by Ola Leifler.
      * Improved RPM packaging (thanks to Kjell Enblom).
      * Various other minor fixes.

0.1 (2004-08-08)

    First public version.
