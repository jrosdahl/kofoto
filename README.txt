 _  __      __       _
| |/ /___  / _| ___ | |_ ___
| ' // _ \| |_ / _ \| __/ _ \
| . \ (_) |  _| (_) | || (_) |
|_|\_\___/|_|  \___/ \__\___/


OVERVIEW
========

Kofoto is a tool for viewing and organizing images.

Actually, Kofoto is a framework with a backend and (currently) two
frontends:

  * A graphical GTK+-based client (gkofoto).
  * A command-line utility (kofoto).

With the clients you can:

  * Organize images in an album tree.
  * Organize images by use of categories.
  * Associate images with attributes.
  * Search for images matching a search expression.

With the graphical client you can also:

  * View images.
  * Rotate images (by use of an external command-line program, e.g.
    jpegtran).
  * Open images in an external program (e.g. The GIMP).

With the command-line client you can also:

  * Generate HTML pages of an album subtree.

See also the file overview.txt in the doc subdirectory.

LICENSE
=======

See COPYING.txt. The license is a BSD-like open source license (see
http://www.opensource.org).


CONTACT
=======

Email: kofoto@rosdahl.net
Web page: http://kofoto.rosdahl.net
Source repository: http://svn.rosdahl.net/kofoto/kofoto


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

     * PyGTK for GTK+ 2.2. Found at:

           http://www.pygtk.org

     * Python Imaging Library. Found at:

           http://www.pythonware.com/products/pil/

     * PySQLite. Found at:

           http://pysqlite.sourceforge.net

   On a Debian GNU/Linux machine, installing the packages python-gtk2,
   python-imaging and python-sqlite should do.


   Installing and running Kofoto
   -----------------------------

   0. Install the prerequisites, if necessary.
   1. Unpack the kofoto-*.tar.gz archive.
   2. Run "python setup.py install" in the created directory to
      install Kofoto at the default location (e.g. /usr/local). See
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

     * GTK+ 2.2 for Windows. Found at:

            http://www.dropline.net/gtk/

     * PyGTK for GTK+ 2.2 for Windows. Found at:

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

To be written.
