"""A set datatype with an interface like sets.py in Python 2.3 but
that stores data in temporary SQL tables."""

# Be compatible with Python 2.2.
from __future__ import generators

class SqlSetFactory:
    """Factory class responsible for creating SqlSet instances."""
    def __init__(self, connection):
        """connection should be an open SQL connection."""
        self.connection = connection
        self.tablecount = 0

    def newSet(self):
        """Create a new SqlSet instance."""
        self.tablecount += 1
        return SqlSet(self.connection, u"foo%d" % self.tablecount)


class SqlSet:
    """A set class that stores integers in a temporary SQL table."""
    def __init__(self, connection, tablename):
        """connection should be an open SQL connection. tablename is
        the unique name to use for the temporary table.
        """
        self.tablename = tablename
        self.connection = connection
        cursor = self.connection.cursor()
        cursor.execute(
            "create temporary table %(myname)s ("
            "    number      integer not null,"
            "    primary key (number)"
            ")" % {"myname": self.tablename})

    def __contains__(self, number):
        cursor = self.connection.cursor()
        cursor.execute(
            "select count(*) from %s where number = %s",
            self.tablename,
            number)
        return int(cursor.fetchone()[0]) > 0

    def __del__(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute("drop table %s" % self.tablename)
        except:
            # The connection has been closed, so the table has already
            # been dropped.
            pass

    def __iter__(self):
        cursor = self.connection.cursor()
        cursor.execute("select * from %s" % self.tablename)
        while True:
            rows = cursor.fetchmany(10)
            if not rows:
                break
            for row in rows:
                yield row[0]

    def __iand__(self, other):
        self.intersection_update(other)
        return self

    def __ior__(self, other):
        self.union_update(other)
        return self

    def __isub__(self, other):
        self.difference_update(other)
        return self

    def add(self, number):
        """Add a number to the set."""
        cursor = self.connection.cursor()
        cursor.execute(
            "insert into %s values (%%s)" % self.tablename,
            number)

    def difference_update(self, other):
        """Update this set with the difference between itself and
        another set."""
        cursor = self.connection.cursor()
        cursor.execute(
            " delete"
            " from %(myname)s"
            " where %(myname)s.number in ("
            "     select * from %(othername)s)" % {
                "myname": self.tablename,
                "othername": other.tablename
            })

    def getTablename(self):
        """Get the name of the temporary table where the set is stored.

        The single column in the table is named "number"."""
        return self.tablename

    def intersection_update(self, other):
        """Update this set with the intersection of itself and another
        set."""
        cursor = self.connection.cursor()
        cursor.execute(
            " delete"
            " from %(myname)s"
            " where %(myname)s.number not in ("
            "     select * from %(othername)s)" % {
                "myname": self.tablename,
                "othername": other.tablename
            })

    def remove(self, number):
        """Remove a number from the set."""
        cursor = self.connection.cursor()
        cursor.execute(
            " delete"
            " from  %s"
            " where number = %%s" % self.tablename,
            number)

    def runQuery(self, query, parameters=()):
        """Run an SQL query with %(tablename)s expanded to the name of
        the temporary table where the set is stored."""
        cursor = self.connection.cursor()
        cursor.execute(query % {"tablename": self.tablename},
                       parameters)
        return cursor.rowcount

    def union_update(self, other):
        """Update this set with the union of itself and another set."""
        cursor = self.connection.cursor()
        cursor.execute(
            " insert"
            " into %(myname)s"
            " select * from %(othername)s"
            " where %(othername)s.number not in ("
            "     select * from %(myname)s)" % {
                "myname": self.tablename,
                "othername": other.tablename
            })
