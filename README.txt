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

0.1 (2004-08-08)

    First public version.
