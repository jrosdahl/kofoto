# LL(1) grammar for search expressions:
#
# <searchexpr> ::= <expr> <eof>
#
# <expr> ::= <andexpr> ("or" <andexpr>)*
#
# <andexpr> ::= <notexpr> ("and" <notexpr>)*
#
# <notexpr> ::= "not" <term> | <term>
#
# <term> ::=   <bareword>                           (a category)
#            | "exactly" <bareword>                 (a category)
#            | <album>
#            | <attribute> <attroper> <attrvalue>
#            | "(" <expr> ")"
#
# <bareword> ::= \w [\w-]*
#
# <album> ::= "/" \w [\w-]*
#
# <attribute> ::= "@" \w [\w-]*
#
# <attroper> ::= "=" | "!=" | "<" | ">" | "<=" | ">="
#
# <attrvalue> ::= <quoted string> | <bareword>
#
# <quoted string> ::= "\"" .* "\""   (where each backslash and quotation mark in
#                                     the .* part is preceeded by a backslash)
# where \w is characters (locale dependent), digits and underscore.

__all__ = [
    "BadTokenError",
    "ParseError",
    "Parser",
    "SearchNodeFactory",
    "UnterminatedStringError",
]

import re
from kofoto.common import KofotoError
import kofoto.shelf

class ParseError(KofotoError):
    pass

class BadTokenError(ParseError):
    pass

class UnterminatedStringError(ParseError):
    pass

class SearchNodeFactory:
    def __init__(self, shelf):
        self._shelf = shelf

    def albumNode(self, tag_or_album):
        if isinstance(tag_or_album, kofoto.shelf.Album):
            album = tag_or_album
        else:
            album = self._shelf.getAlbum(tag_or_album)
        return AlbumSearchNode(album.getId())

    def andNode(self, subnodes):
        return AndSearchNode(subnodes)

    def attrcondNode(self, name, operator, value):
        assert operator in ["=", "!=", "<", ">", "<=", ">="]
        return AttributeConditionSearchNode(name, operator, value)

    def categoryNode(self, tag_or_category, recursive=False):
        if isinstance(tag_or_category, kofoto.shelf.Category):
            category = tag_or_category
        else:
            category = self._shelf.getCategory(tag_or_category)
        if recursive:
            catids = list(self._shelf.categorydag.get().getDescendants(
                category.getId()))
        else:
            catids = [category.getId()]
        return CategorySearchNode(catids)

    def notNode(self, subnode):
        return NotSearchNode(subnode)

    def orNode(self, subnodes):
        return OrSearchNode(subnodes)


class Parser:
    def __init__(self, shelf):
        self._snfactory = SearchNodeFactory(shelf)

    def parse(self, string):
        assert isinstance(string, unicode), "non-Unicode search string"
        self._scanner = Scanner(string)
        return self.searchexpr()

    def searchexpr(self):
        expr = self.expr()
        kind, token = self._scanner.next()
        if kind != "eof":
            raise (ParseError,
                   "expected end of expression or conjunction, got: " + token)
        return expr

    def expr(self):
        andexprs = [self.andexpr()]
        while True:
            kind, token = self._scanner.next()
            if kind != "or":
                self._scanner.rewind()
                break
            andexprs.append(self.andexpr())
        if len(andexprs) == 1:
            return andexprs[0]
        else:
            return self._snfactory.orNode(andexprs)

    def andexpr(self):
        notexprs = [self.notexpr()]
        while True:
            kind, token = self._scanner.next()
            if kind != "and":
                self._scanner.rewind()
                break
            notexprs.append(self.notexpr())
        if len(notexprs) == 1:
            return notexprs[0]
        else:
            return self._snfactory.andNode(notexprs)

    def notexpr(self):
        kind, token = self._scanner.next()
        if kind == "not":
            return self._snfactory.notNode(self.term())
        else:
            self._scanner.rewind()
            return self.term()

    def term(self):
        kind, token = self._scanner.next()
        if kind == "bareword":
            return self._snfactory.categoryNode(token, recursive=True)
        elif kind == "exactly":
            kind, token = self._scanner.next()
            if kind != "bareword":
                raise ParseError, \
                      "expected category tag after \"exactly\", got: " + token
            return self._snfactory.categoryNode(token, recursive=False)
        elif kind == "album":
            return self._snfactory.albumNode(token[1:])
        elif kind == "attribute":
            attribute = token
            kind, token = self._scanner.next()
            if kind in ["ne", "eq", "le", "ge", "lt", "gt"]:
                attroper = token
            else:
                raise ParseError, \
                      "expected comparison operator, got: " + token
            kind, token = self._scanner.next()
            if kind in ("bareword", "string"):
                value = token
            else:
                raise ParseError, \
                      "expected bareword or quoted string, got: " + token
            return self._snfactory.attrcondNode(attribute[1:], attroper, value)
        elif kind == "lparen":
            expr = self.expr()
            kind, token = self._scanner.next()
            if kind != "rparen":
                raise ParseError, \
                      "expected right parenthesis or conjunction, got: " + token
            return expr
        raise ParseError, "expected expression, got: " + token

######################################################################

class AlbumSearchNode:
    def __init__(self, albumid):
        self._id = albumid

    def __repr__(self):
        return "AlbumSearchNode(%r)" % self._id

    __str__ = __repr__

    def getQuery(self):
        return (" select distinct objectid"
                " from   member"
                " where  albumid = %s" % self._id)

class AndSearchNode:
    def __init__(self, subnodes):
        self._subnodes = subnodes

    def __repr__(self):
        return "AndSearchNode(%s)" % ", ".join(
            [repr(x) for x in self._subnodes])

    __str__ = __repr__

    def getQuery(self):
        categories = []
        attrconds = []
        others = []
        for node in self._subnodes:
            if isinstance(node, CategorySearchNode):
                categories.append(node)
            elif isinstance(node, AttributeConditionSearchNode):
                attrconds.append(node)
            else:
                others.append(node)

        tables = []
        andclauses = []
        if categories and attrconds:
            andclauses.append("oc0.objectid = a0.objectid")
        if categories:
            first = True
            for ix in range(len(categories)):
                tables.append("object_category as oc%d" % ix)
                if first:
                    first = False
                else:
                    andclauses.append("oc0.objectid = oc%d.objectid" % ix)
                andclauses.append(
                    "oc%d.categoryid in (%s)" % (
                    ix,
                    ",".join([str(x) for x in categories[ix].getIds()])))
        if attrconds:
            first = True
            for ix in range(len(attrconds)):
                tables.append("attribute as a%d" % ix)
                if first:
                    first = False
                else:
                    andclauses.append("a0.objectid = a%d.objectid" % ix)
                andclauses.append(
                    "a%d.name = '%s' and a%d.lcvalue %s '%s'" % (
                        ix,
                        attrconds[ix].getAttributeName(),
                        ix,
                        attrconds[ix].getOperator(),
                        attrconds[ix].getAttributeValue().replace("'", "''")))
        if categories:
            selectvar = "oc0.objectid"
        elif attrconds:
            selectvar = "a0.objectid"
        else:
            selectvar = "objectid"
            tables.append("object")

        if others:
            for node in others:
                andclauses.append("%s in (%s)" % (
                    selectvar,
                    node.getQuery()))

        return (" select distinct %s"
                " from   %s"
                " where  %s" % (
                    selectvar,
                    ", ".join(tables),
                    " and ".join(andclauses)))


class AttributeConditionSearchNode:
    def __init__(self, attrname, operator, value):
        self._name = attrname
        if operator == "=":
            self._operator = "glob"
        elif operator == "!=":
            self._operator = "not glob"
        else:
            self._operator = operator
        self._value = value.lower()
        if operator in ["=", "!="]:
            # "?" won't match a non-ASCII character in UTF-8 encoding
            # unless SQLite is compiled with UTF-8 support, and that's
            # not the case in most builds.
            self._value = self._value.replace("?", "*")

    def __repr__(self):
        return "AttributeConditionSearchNode(%r, %r, %r)" % (
            self._name, self._operator, self._value)

    __str__ = __repr__

    def getAttributeName(self):
        return self._name

    def getAttributeValue(self):
        return self._value

    def getOperator(self):
        return self._operator

    def getQuery(self):
        return (" select distinct objectid"
                " from   attribute"
                " where  name = '%s' and lcvalue %s '%s'" % (
                    self._name,
                    self._operator,
                    self._value.replace("'", "''")))

class CategorySearchNode:
    def __init__(self, ids):
        self._ids = ids

    def __repr__(self):
        return "CategorySearchNode(%r)" % self._ids

    __str__ = __repr__

    def getQuery(self):
        return (" select distinct objectid"
                " from   object_category"
                " where  categoryid in (%s)" % (
                    ",".join([str(x) for x in self._ids])))

    def getIds(self):
        return self._ids

class OrSearchNode:
    def __init__(self, subnodes):
        self._subnodes = subnodes

    def __repr__(self):
        return "OrSearchNode(%s)" % ", ".join(
            [repr(x) for x in self._subnodes])

    __str__ = __repr__

    def getQuery(self):
        catids = []
        attrconds = []
        others = []
        for node in self._subnodes:
            if isinstance(node, CategorySearchNode):
                catids += node.getIds()
            elif isinstance(node, AttributeConditionSearchNode):
                attrconds.append(node)
            else:
                others.append(node)

        selects = []
        if catids:
            selects.append(
                " select distinct objectid"
                " from   object_category"
                " where  categoryid in (%s)" % (
                    ",".join([str(x) for x in catids])))
        if attrconds:
            orclauses = []
            for attrcond in attrconds:
                orclauses.append(
                    "name = '%s' and lcvalue %s '%s'" % (
                        attrcond.getAttributeName(),
                        attrcond.getOperator(),
                        attrcond.getAttributeValue().replace("'", "''")))
            selects.append(
                " select distinct objectid"
                " from   attribute"
                " where  %s" % (
                    " or ".join(orclauses)))
        if others:
            selects += [x.getQuery() for x in others]
        return " union ".join(selects)

class NotSearchNode:
    def __init__(self, subnode):
        self._subnode = subnode

    def __repr__(self):
        return "NotSearchNode(%r)" % self._subnode

    __str__ = __repr__

    def getQuery(self):
        return (" select objectid"
                " from   object"
                " where  objectid not in (%s)" % self._subnode.getQuery())

class Scanner:
    _whiteRegexp = re.compile(r"\s*", re.LOCALE | re.MULTILINE)
    _tokenRegexps = [
        (re.compile(x, re.IGNORECASE | re.LOCALE | re.MULTILINE), y)
        for (x, y) in [
            (r"\(", "lparen"),
            (r"\)", "rparen"),
            (r"/\w[\w-]*", "album"),
            (r"@\w[\w-]*", "attribute"),
            (r'"([^\\]|\\(.|$))*?"', "string"),
            (r'"([^\\]|\\(.|$))*$', "untermstring"),
            (r"!=", "ne"),
            (r"=", "eq"),
            (r"<=", "le"),
            (r">=", "ge"),
            (r"<", "lt"),
            (r">", "gt"),
            (r"and\b", "and"),
            (r"exactly\b", "exactly"),
            (r"or\b", "or"),
            (r"not\b", "not"),
            (r"\w[\w-]*", "bareword"),
            (r"$", "eof"),
            ]]

    def __init__(self, string):
        self._string = string
        self._nexttoken = None
        self._pos = 0
        self.dorewind = False

    def __iter__(self):
        return self

    def next(self):
        if self.dorewind:
            self.dorewind = False
        else:
            self.currenttoken = self._next()
        return self.currenttoken

    def rewind(self):
        self.dorewind = True

    def _eatWhite(self):
        nwhite = self._whiteRegexp.match(self._string).end()
        self._pos += nwhite
        self._string = self._string[nwhite:]

    def _next(self):
        self._eatWhite()
        for tokenregexp, kind in self._tokenRegexps:
            m = tokenregexp.match(self._string)
            if m:
                token = m.group(0)
                if kind == "untermstring":
                    raise UnterminatedStringError, self._pos
                if kind == "string":
                    token = re.sub(r"\\(.)", r"\1", token[1:-1])
                self._pos += m.end()
                self._string = self._string[m.end():]
                return kind, token
        raise BadTokenError, self._pos
