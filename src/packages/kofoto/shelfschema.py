"""Schema of the metadata database."""

schema = """
    -- EER diagram without attributes:
    --
    --                                          .----.
    --                                        ,'      |
    --                   ,^.                ,' N    ,^.
    --                 ,'   '.  N +----------+    ,'   '.
    --                <  has  >===| category |---< child >
    --                 '.   .'    +----------+ 0  '.   .'
    --                   'v'                        'v'
    --                    | 0
    --                    |           ,^.
    --              N +--------+ 0  ,'   '.  N +-----------+
    --      .---------| object |---<  has  >===| attribute |
    --      |         +--------+    '.   ,'    +-----------+
    --    ,/\.          |    |        'v'
    --  ,'    '.     __/      \__
    -- < member >   |            |
    --  '.    ,'   \|/          \|/
    --    '\/'      |            |
    --      | 1 +-------+    +-------+
    --      '---| album |    | image |
    --          +-------+    +-------+
    --                        1 | | 1
    --                       ,-'   '-.
    --                     ,^.       ,^.
    --                   ,'   '.   ,'   '.
    --                  <  has  > <primary>
    --                   '.   .'   '.   .'
    --                     'v'       'v'
    --                     N \       / 0..1
    --                      +---------+
    --                      | version |
    --                      +---------+
    --
    --        |
    -- where \|/ is supposed to look like the subclass relation symbol.
    --        |

    BEGIN;

    -- Administrative information about the database.
    CREATE TABLE dbinfo (
        version     INTEGER NOT NULL
    );

    -- Superclass of objects in an album.
    CREATE TABLE object (
        -- Identifier of the object.
        id          INTEGER NOT NULL,

        PRIMARY KEY (id)
    );

    -- Albums in the shelf. Subclass of object.
    CREATE TABLE album (
        -- Identifier of the album. Shared primary key with object.
        id          INTEGER NOT NULL,
        -- Human-memorizable tag.
        tag         VARCHAR(256) NOT NULL,
        -- Whether it is possible to delete the album.
        deletable   INTEGER NOT NULL,
        -- Album type (plain, orphans or search).
        type        VARCHAR(256) NOT NULL,

        UNIQUE      (tag),
        FOREIGN KEY (id) REFERENCES object,
        PRIMARY KEY (id)
    );

    -- Images in the shelf. Subclass of object.
    CREATE TABLE image (
        -- Internal identifier of the image. Shared primary key with
        -- object.
        id          INTEGER NOT NULL,

        -- The primary version. NULL if no such version exists.
        primary_version INTEGER,

        FOREIGN KEY (id) REFERENCES object,
        FOREIGN KEY (primary_version) REFERENCES image_version,
        PRIMARY KEY (id)
    );

    -- Image versions.
    CREATE TABLE image_version (
        -- Identifier of the image version.
        id          INTEGER NOT NULL,

        -- Identifier of the image associated with this version.
        image       INTEGER NOT NULL,

        -- Type (original, important or other).
        type        VARCHAR(20) NOT NULL,

        -- Arbitrary comment about the version.
        comment     TEXT NOT NULL,

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
        
        FOREIGN KEY (image) REFERENCES image,
        UNIQUE      (hash),
        PRIMARY KEY (id)
    );

    CREATE INDEX image_version_image_index ON image_version (image);
    CREATE INDEX image_version_location_index ON image_version (directory, filename);

    -- Members in an album.
    CREATE TABLE member (
        -- Identifier of the album.
        album       INTEGER NOT NULL,
        -- Member position, from 0 and up.
        position    UNSIGNED NOT NULL,
        -- Key of the member object.
        object      INTEGER NOT NULL,

        FOREIGN KEY (album) REFERENCES album,
        FOREIGN KEY (object) REFERENCES object,
        PRIMARY KEY (album, position)
    );

    CREATE INDEX member_object_index ON member (object);

    -- Attributes for objects.
    CREATE TABLE attribute (
        -- Key of the object.
        object      INTEGER NOT NULL,
        -- Name of the attribute.
        name        TEXT NOT NULL,
        -- Value of the attribute.
        value       TEXT NOT NULL,
        -- Lowercased value of the attribute.
        lcvalue     TEXT NOT NULL,

        FOREIGN KEY (object) REFERENCES object,
        PRIMARY KEY (object, name)
    );

    -- Categories in the shelf.
    CREATE TABLE category (
        -- Key of the category.
        id          INTEGER NOT NULL,
        -- Human-memorizable tag.
        tag         TEXT NOT NULL,
        -- Short description of the category.
        description TEXT NOT NULL,

        UNIQUE      (tag),
        PRIMARY KEY (id)
    );

    -- Parent-child relations between categories.
    CREATE TABLE category_child (
        -- Parent category.
        parent      INTEGER NOT NULL,

        -- Child category.
        child       INTEGER NOT NULL,

        FOREIGN KEY (parent) REFERENCES category,
        FOREIGN KEY (child) REFERENCES category,
        PRIMARY KEY (parent, child)
    );

    CREATE INDEX category_child_child ON category_child (child);

    -- Category-object mapping.
    CREATE TABLE object_category (
        -- Object.
        object      INTEGER NOT NULL,

        -- Category.
        category    INTEGER NOT NULL,

        FOREIGN KEY (object) REFERENCES object,
        FOREIGN KEY (category) REFERENCES category,
        PRIMARY KEY (object, category)
    );

    CREATE INDEX object_category_category ON object_category (category);

    COMMIT;
"""
