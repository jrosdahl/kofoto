__all__ = ["upgradeShelf"]

import os

def upgradeShelf(connection, fromVersion, toVersion):
    # ----------------------------------------------------------------
    if fromVersion < 1:
        #
        # Split image location field into directory and filename.
        #
        cursor = connection.cursor()
        cursor2 = connection.cursor()
        cursor.execute(
            " create temporary table tmp_image ("
            "     imageid   integer not null,"
            "     hash      char(32) not null,"
            "     directory varchar(256) not null,"
            "     filename  varchar(256) not null"
            " )")
        cursor.execute(
            "select imageid, hash, location from image")
        for imageid, hash, location in cursor:
            cursor2.execute(
                "insert into tmp_image values (%s, %s, %s, %s)",
                imageid,
                hash,
                os.path.dirname(location),
                os.path.basename(location))
        cursor.execute(
            "drop table image")
        cursor.execute(
            """
    CREATE TABLE image (
        -- Internal identifier of the image. Shared primary key with
        -- object.
        imageid     INTEGER NOT NULL,
        -- Identifier string which is derived from the image data and
        -- identifies the image uniquely. Currently an MD5 checksum
        -- (in hex format) of all image data.
        hash        CHAR(32) NOT NULL,
        -- Directory part of the last known location (local pathname)
        -- of the image.
        directory   VARCHAR(256) NOT NULL,
        -- Filename part of the last known location (local pathname)
        -- of the image.
        filename    VARCHAR(256) NOT NULL,

        UNIQUE      (hash),
        FOREIGN KEY (imageid) REFERENCES object,
        PRIMARY KEY (imageid)
    )""")
        cursor.execute(
            "CREATE INDEX image_location_index ON image (directory, filename)")
        cursor.execute(
            " insert into image (imageid, hash, directory, filename)"
            " select imageid, hash, directory, filename from tmp_image")
        cursor.execute(
            "drop table tmp_image")

    # ----------------------------------------------------------------
    if fromVersion < 2:
        #
        # Add mtime, width and height columns to the image table.
        # Width and height is taken from the old width and height
        # attributes.
        #
        cursor = connection.cursor()
        cursor2 = connection.cursor()
        cursor.execute(
            " create temporary table tmp_image ("
            "     imageid   integer not null,"
            "     hash      char(32) not null,"
            "     directory varchar(256) not null,"
            "     filename  varchar(256) not null,"
            "     mtime     integer not null,"
            "     width     integer not null,"
            "     height    integer not null"
            " )")
        cursor.execute(
            "select imageid, hash, directory, filename from image")
        for imageid, hash, directory, filename in cursor:
            cursor2.execute(
                " select value"
                " from   attribute"
                " where  objectid = %s and name = 'width'",
                imageid)
            width = cursor2.fetchone()[0]
            cursor2.execute(
                " select value"
                " from   attribute"
                " where  objectid = %s and name = 'height'",
                imageid)
            height = cursor2.fetchone()[0]
            try:
                mtime = os.path.getmtime(os.path.join(directory, filename))
            except OSError:
                mtime = 0
            cursor2.execute(
                "insert into tmp_image values (%s, %s, %s, %s, %s, %s, %s)",
                imageid,
                hash,
                directory,
                filename,
                mtime,
                width,
                height)
        cursor.execute(
            "drop table image")
        cursor.execute(
            """
    CREATE TABLE image (
        -- Internal identifier of the image. Shared primary key with
        -- object.
        imageid     INTEGER NOT NULL,
        -- Identifier string which is derived from the image data and
        -- identifies the image uniquely. Currently an MD5 checksum
        -- (in hex format) of all image data.
        hash        CHAR(32) NOT NULL,
        -- Directory part of the last known location (local pathname)
        -- of the image.
        directory   VARCHAR(256) NOT NULL,
        -- Filename part of the last known location (local pathname)
        -- of the image.
        filename    VARCHAR(256) NOT NULL,
        -- Last known time of modification (UNIX epoch time).
        mtime       INTEGER NOT NULL,
        -- Image width.
        width       INTEGER NOT NULL,
        -- Image height.
        height      INTEGER NOT NULL,

        UNIQUE      (hash),
        FOREIGN KEY (imageid) REFERENCES object,
        PRIMARY KEY (imageid)
    );""")
        cursor.execute(
            "CREATE INDEX image_location_index ON image (directory, filename)")
        cursor.execute(
            " insert into image (imageid, hash, directory, filename,"
            "                    mtime, width, height)"
            " select imageid, hash, directory, filename, mtime, width, height"
            " from   tmp_image")
        cursor.execute(
            "drop table tmp_image")
        cursor.execute(
            "delete from attribute where name in ('width', 'height')")

    # ----------------------------------------------------------------
    cursor = connection.cursor()
    cursor.execute(
        " update dbinfo"
        " set    version = %s",
        toVersion)
    connection.commit()
