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
        return AlbumSearchNode(self._shelf, album)

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
            raise ParseError, \
                "expected end of expression or conjunction, got: \"%s\"" % token
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
                      "expected category tag after \"exactly\", got: \"%s\"" % token
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
                      "expected comparison operator, got: \"%s\"" % token
            kind, token = self._scanner.next()
            if kind in ("bareword", "string"):
                value = token
            else:
                raise ParseError, \
                      "expected bareword or quoted string, got: \"%s\"" % token
            return self._snfactory.attrcondNode(attribute[1:], attroper, value)
        elif kind == "lparen":
            expr = self.expr()
            kind, token = self._scanner.next()
            if kind != "rparen":
                raise ParseError, \
                      "expected right parenthesis or conjunction, got: \"%s\"" % token
            return expr
        raise ParseError, "expected expression, got: \"%s\"" % token

######################################################################

class AlbumSearchNode:
    def __init__(self, shelf, album):
        self._shelf = shelf
        self._album = album

    def __repr__(self):
        return "AlbumSearchNode(%r)" % (self._album)

    __str__ = __repr__

    def getQuery(self):
        t = self._album.getType()
        if t == "allalbums":
            return "select 1 where null" # Return empty result set.
        elif t == "allimages":
            return (" select i.id"
                    " from   image as i left join attribute as a"
                    "            on i.id = a.object and a.name = 'captured'"
                    " order by a.lcvalue, i.directory, i.filename")
        elif t == "orphans":
            return (" select i.id"
                    " from   image as i left join attribute as a"
                    " on     i.id = a.object and a.name = 'captured'"
                    " where  i.id not in (select object from member)"
                    " order by a.lcvalue, i.directory, i.filename")
        elif t == "plain":
            return (" select distinct object"
                    " from   member"
                    " where  album = %s" % self._album.getId())
        elif t == "search":
            query = self._album.getAttribute(u"query")
            if not query:
                return ""
            parser = Parser(self._shelf)
            tree = parser.parse(query)
            return tree.getQuery()
        else:
            assert False, ("Unknown album type", t)

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
            andclauses.append("oc0.object = a0.object")
        if categories:
            first = True
            for ix in range(len(categories)):
                tables.append("object_category as oc%d" % ix)
                if first:
                    first = False
                else:
                    andclauses.append("oc0.object = oc%d.object" % ix)
                andclauses.append(
                    "oc%d.category in (%s)" % (
                    ix,
                    ",".join([str(x) for x in categories[ix].getIds()])))
        if attrconds:
            first = True
            for ix in range(len(attrconds)):
                tables.append("attribute as a%d" % ix)
                if first:
                    first = False
                else:
                    andclauses.append("a0.object = a%d.object" % ix)
                andclauses.append(
                    "a%d.name = '%s' and a%d.lcvalue %s '%s'" % (
                        ix,
                        attrconds[ix].getAttributeName(),
                        ix,
                        attrconds[ix].getOperator(),
                        attrconds[ix].getAttributeValue().replace("'", "''")))
        if categories:
            selectvar = "oc0.object"
        elif attrconds:
            selectvar = "a0.object"
        else:
            selectvar = "id"
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
        return (" select distinct object"
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
        return (" select distinct object"
                " from   object_category"
                " where  category in (%s)" % (
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
                " select distinct object"
                " from   object_category"
                " where  category in (%s)" % (
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
                " select distinct object"
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
        return (" select id"
                " from   object"
                " where  id not in (%s)" % self._subnode.getQuery())

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
