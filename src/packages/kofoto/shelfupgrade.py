"""Implementation of code that upgrades the shelf to a newer format."""

__all__ = ["isUpgradable", "upgradeShelf"]

import os
import sqlite3 as sql
import time
import kofoto.shelfschema
from kofoto.shelfexceptions import ShelfLockedError, ShelfNotFoundError

def isUpgradable(location):
    """Check whether a shelf is upgradable, i.e. not the latest version."""

    if not os.path.exists(location):
        raise ShelfNotFoundError(location)
    try:
        connection = sql.connect(location)
        cursor = connection.cursor()
        cursor.execute("select version from dbinfo")
        version = cursor.fetchone()[0]
        if version == 2:
            return True
        else:
            return False
    except sql.OperationalError:
        raise ShelfLockedError(location)
    except sql.DatabaseError:
        raise ShelfNotFoundError(location)

def tryUpgrade(location, toVersion):
    """Upgrade the database format.

    Returns True if upgrade was successful, otherwise False.
    """

    connection = sql.connect(location)
    cursor = connection.cursor()
    cursor.execute("select version from dbinfo")
    fromVersion = cursor.fetchone()[0]
    connection.rollback()

    if fromVersion < 2:
        return False

    # ----------------------------------------------------------------
    if fromVersion < 3:
        new_location = "%s-new-%s" % (
            location, time.strftime("%Y%m%d-%H%M%S"))
        connection = sql.connect(new_location, client_encoding="UTF-8")
        cursor = connection.cursor()
        cursor.execute(kofoto.shelfschema.schema)
        cursor.execute("attach '%s' as old" % (location,))
        for tablename in ["dbinfo", "object", "album", "member",
                          "attribute", "category", "category_child",
                          "object_category"]:
            cursor.execute("insert into %s select * from old.%s" % (
                tablename, tablename))
        cursor.execute(
            " insert into image (id, primary_version)"
            " select imageid, imageid"
            " from   old.image")
        cursor.execute(
            " insert into image_version"
            "     (id, image, type, hash, directory, filename, mtime,"
            "      width, height, comment)"
            " select imageid, imageid, 'original', hash, directory, filename,"
            "        mtime, width, height, ''"
            " from   old.image")
        cursor.execute(
            " select id"
            " from   album"
            " where  type in ('allalbums', 'allimages')")
        aids = [x[0] for x in cursor]
        if aids:
            aids_str = ",".join([str(x) for x in aids])
            cursor.execute(
                " delete from album"
                " where  id in (?)" % (aids_str,))
            cursor.execute(
                " delete from object"
                " where  id in (?)" % (aids_str,))
            cursor.execute(
                " delete from member"
                " where  album in (?)" % (aids_str,))
            cursor.execute(
                " delete from attribute"
                " where  object in (?)" % (aids_str,))
        cursor.execute(
            " update dbinfo"
            " set    version = ?",
            (toVersion,))
        connection.commit()
        del connection # Drop file handle; needed on Windows.
        os.rename(location, "%s-backup-%s" % (
            location, time.strftime("%Y%m%d-%H%M%S")))
        os.rename(new_location, location)
    return True
