# Disable check for exception type except clause (see cmdInspectPath):
# pylint: disable-msg=W0702

"""Main Kofoto commandline client code."""

__all__ = ["main"]

import codecs
import getopt
import os
import sys
import time

from kofoto.clientenvironment import ClientEnvironment, ClientEnvironmentError
from kofoto.clientutils import \
    DIRECTORIES_TO_IGNORE, \
    expanduser, \
    get_file_encoding, \
    walk_files
from kofoto.albumtype import AlbumType
from kofoto.config import DEFAULT_CONFIGFILE_LOCATION
from kofoto.imageversiontype import ImageVersionType
from kofoto.search import \
    BadTokenError, ParseError, Parser, UnterminatedStringError
from kofoto.shelf import \
    computeImageHash, \
    makeValidTag
from kofoto.shelfexceptions import \
    AlbumDoesNotExistError, \
    AlbumExistsError, \
    BadAlbumTagError, \
    BadCategoryTagError, \
    CategoriesAlreadyConnectedError, \
    CategoryDoesNotExistError, \
    CategoryExistsError, \
    CategoryLoopError, \
    CategoryPresentError, \
    ExifImportError, \
    ImageDoesNotExistError, \
    ImageVersionDoesNotExistError, \
    ImageVersionExistsError, \
    MultipleImageVersionsAtOneLocationError, \
    NotAnImageFileError, \
    ObjectDoesNotExistError, \
    ShelfLockedError, \
    ShelfNotFoundError, \
    UndeletableAlbumError, \
    UnknownAlbumTypeError, \
    UnknownImageVersionTypeError, \
    UnsettableChildrenError, \
    UnsupportedShelfError

######################################################################
### Constants.

PRINT_ALBUMS_INDENT = 4

######################################################################
### Exceptions.

class ArgumentError(Exception):
    """Bad arguments to command."""
    pass

######################################################################
### Help text data.

optionDefinitionList = [
    ("    --configfile FILE",
     "Use configuration file FILE instead of the default (%s)." % (
         DEFAULT_CONFIGFILE_LOCATION)),
    ("    --database FILE",
     "Use the metadata database FILE instead of the default (specified in the"
     " configuration file)."),
    ("    --gencharenc ENCODING",
     "Generate HTML pages with character encoding ENCODING instead of the"
     " default (utf-8)."),
    ("-h, --help",
     "Display this help."),
    ("    --identify-by-hash",
     "Identify image versions by hash. This is the default."),
    ("    --identify-by-path",
     "Identify image versions by path."),
    ("    --ids",
     "Print ID numbers instead of locations."),
    ("    --include-all",
     "Include all image versions for images matching a search expression."),
    ("    --include-important",
     "Include all image versions with type \"important\" for images matching a"
     " search expression."),
    ("    --include-original",
     "Include all image versions with type \"original\" for images matching a"
     " search expression."),
    ("    --include-other",
     "Include all image versions with type \"other\" for images matching a"
     " search expression."),
    ("    --include-primary",
     "Include all primary image versions for images matching a search"
     " expression."),
    ("    --no-act",
     "Do everything which is supposed to be done, but don't commit any changes"
     " to the database."),
    ("-0, --null",
     "Use null characters instead of newlines when printing image version"
     " locations. This is mainly useful in combination with \"xargs"
     " --null\"."),
    ("    --position POSITION",
     "Add/register to position POSITION. Default: last."),
    ("-t, --type TYPE",
     "Use album type TYPE when creating an album or output type TYPE when"
     " generating output."),
    ("-v, --verbose",
      "Be verbose (and slower)."),
    ("    --version",
     "Print version to standard output."),
    ]

albumAndImageCommandsDefinitionList = [
    ("add-category CATEGORY OBJECT [OBJECT ...]",
     "Add a category to the given objects."),
    ("delete-attribute ATTRIBUTE OBJECT [OBJECT ...]",
     "Delete an attribute from the given objects."),
    ("get-attribute ATTRIBUTE OBJECT",
     "Get an attribute's value for an object."),
    ("get-attributes OBJECT",
     "Get attributes for an object."),
    ("get-categories OBJECT",
     "Get categories for an object."),
    ("remove-category CATEGORY OBJECT [OBJECT ...]",
     "Remove a category from the given objects."),
    ("search SEARCHEXPRESSION",
     "Search for images matching an expression and print image version"
     " locations on standard output (or image IDs if the --ids option is"
     " given) separated by newlines (or by null characters if --null is"
     " given). By default, only primary image versions are printed, but other"
     " versions can be printed by supplying one or several of the options"
     " --include-all, --include-important, --include-original and"
     " --include-other. (If no --include-* option is supplied,"
     " --include-primary is assumed.)"),
    ("set-attribute ATTRIBUTE VALUE OBJECT [OBJECT ...]",
     "Set ATTRIBUTE to VALUE for the given objects."),
    ]

albumCommandsDefinitionList = [
    ("add ALBUM OBJECT [OBJECT ...]",
     "Add the given objects (albums and images) to the album ALBUM. (The"
     " objects are placed last if a position is not specified with"
     " --position.)"),
    ("create-album TAG",
     "Create an empty, unlinked album with tag TAG. If a type argument is not"
     " given with -t/--type, an album of type \"plain\" will be created."),
    ("destroy-album ALBUM [ALBUM ...]",
     "Destroy the given albums permanently. All metadata is also destroyed,"
     " but not the album's children."),
    ("generate ROOTALBUM DIRECTORY [SUBALBUM ...]",
     "Generate output for ROOTALBUM in the directory DIRECTORY. If subalbums"
     " are given, only generate those albums, their descendants and their"
     " immediate parents. Use -t/--type to use another output type than the"
     " default."),
    ("print-albums [ALBUM]",
     "Print the album graph for ALBUM (default: root). If -v/--verbose is"
     " given, also print images and attributes."),
    ("register ALBUM PATH [PATH ...]",
     "Register objects (i.e. directories and images) and add them to the album"
     " ALBUM. (The objects are placed last.) Directories are recursively"
     " scanned for other directories and images, which also will be"
     " registered."),
    ("remove ALBUM POSITION [POSITION ...]",
     "Remove the objects at the given positions from ALBUM."),
    ("rename-album OLDTAG NEWTAG",
     "Rename album tag."),
    ("sort-album ALBUM [ATTRIBUTE]",
     "Sort the contents of ALBUM by an attribute (default: captured)."),
    ]

imageCommandsDefinitionList = [
    ("destroy-image IMAGE [IMAGE ...]",
     "Destroy the given images permanently. All metadata and image versions"
     " are also destroyed (but not the image files on disk)."),
    ("get-imageversions IMAGE",
     "Print image versions for an image. If -v/--verbose is given, print more"
     " information."),
    ]

imageversionCommandsDefinitionList = [
    ("destroy-imageversion IMAGEVERSION [IMAGEVERSION ...]",
     "Destroy the given image versions permanently. All metadata is also"
     " destroyed (but not the image files on disk)."),
    ("find-missing-imageversions",
     "Find missing image versions and print them to standard output."),
    ("find-modified-imageversions",
     "Find modified image versions and print them to standard output."),
    ("inspect-path PATH [PATH ...]",
     "Traverse the given paths and print whether each found file is a"
     " registered, modified, moved or unregistered image version or a"
     " non-image."),
    ("make-primary IMAGEVERSION [IMAGEVERSION ...]",
     "Make an image version the primary version."),
    ("reread-exif IMAGEVERSION [IMAGEVERSION ...]",
     "Reread EXIF information for the given image versions."),
    ("set-imageversion-comment VALUE IMAGEVERSION [IMAGEVERSION ...]",
     "Set comment of the given image versions."),
    ("set-imageversion-image IMAGE IMAGEVERSION [IMAGEVERSION ...]",
     "Set the image to which the given image versions belong."),
    ("set-imageversion-type IMAGEVERSIONTYPE IMAGEVERSION [IMAGEVERSION ...]",
     "Set type of the given image versions."),
    ("update-contents PATH [PATH ...]",
     "Traverse the given paths recursively and remember the new contents"
     " (checksum, width and height) of found image versions."),
    ("update-locations PATH [PATH ...]",
     "Traverse the given paths recursively and remember the new locations of"
     " found image versions."),
    ]

categoryCommandsDefinitionList = [
    ("connect-category PARENTCATEGORY CHILDCATEGORY",
     "Make a category a child of another category."),
    ("disconnect-category PARENTCATEGORY CHILDCATEGORY",
     "Remove parent-child realationship bewteen two categories."),
    ("create-category TAG DESCRIPTION",
     "Create category."),
    ("destroy-category CATEGORY [CATEGORY ...]",
     "Destroy category permanently."),
    ("print-categories",
     "Print category tree."),
    ("rename-category OLDTAG NEWTAG",
     "Rename category tag."),
    ("set-category-description TAG DESCRIPTION",
     "Set category description."),
    ]

miscellaneousCommandsDefinitionList = [
    ("clean-cache",
     "Clean up the image cache (remove left-over generated images)."),
    ("print-statistics",
     "Print some statistics about the database."),
    ]

parameterSemanticsDefinitionList = [
    ("ALBUM",
     "An integer ID or an album tag (see TAG)."),
    ("ATTRIBUTE",
     "An arbitrary attribute name."),
    ("CATEGORY",
     "A category tag (see TAG)."),
    ("DESCRIPTION",
     "An arbitrary string."),
    ("ENCODING",
     "An encoding parsable by Python, e.g. utf-8, latin1 or iso-8859-1."),
    ("FILE",
     "A path to a file."),
    ("IMAGE",
     "An integer ID or a path to an image version file. If it's a path to an"
     " image version, its corresponding image is selected. If"
     " --identify-by-path is given, the path is used for identifying the image"
     " version; otherwise the file's content is used for identification."),
    ("IMAGEVERSION",
     "An integer ID or a path to an image version file. If --identify-by-path"
     " is given, the path is used for identifying the image version; otherwise"
     " the file's contents used for identification."),
    ("IMAGEVERSIONTYPE",
     "\"important\", \"original\" or \"other\"."),
    ("OBJECT",
     "An integer ID, an album tag (see TAG) or a path to an image version"
     " file. If it's a path to an image version, its corresponding image is"
     " selected. If --identify-by-path is given, the path is used for"
     " identifying the image version; otherwise the file's contents used for"
     " identification."),
    ("PATH",
     "A path to a directory or a file."),
    ("POSITION",
     "An integer specifying an index into an album's children. 0 is the first"
     " position, 1 is the second, and so on."),
    ("SEARCHEXPRESSION",
     "A search expression."
     " See http://kofoto.rosdahl.net/trac/wiki/SearchExpressions for more"
     " information."),
    ("TAG",
     "A text string not containing space or @ characters and not consisting"
     " solely of integers."),
    ("TYPE",
     "An album type (as listed below) or an HTML output type (for the moment,"
     " only \"woolly\" is allowed)."),
    ("VALUE",
     "An arbitrary string."),
    ]

albumTypesDefinitionList = [
    ("orphans",
     "All albums and images that don't exist in any plain album."),
    ("plain",
     "An ordinary container that holds albums and images."),
    ("search",
     "An album containing the albums and images that match a search string"
     " (sorted by capture timestamp). The search string is read from the"
     " album's \"query\" attribute."),
    ]

######################################################################
### Helper functions.

def printDefinitionList(deflist, outfile, tindent, dindent, width):
    """Print a properly indented and wrapped definition list.

    A definition list is a list of two-tuples where the first element
    of the tuple is a string containing some term and the second
    element of the tuple is the textual description of the term.

    Arguments:

    deflist -- The definition list.
    outfile -- The file to which the formatted definition list should
               be written.
    tindent -- An integer specifying the left margin of the terms.
    dindent -- An integer specifying the left margin of the descriptions.
    width   -- An integer specifying the right margin of the descriptions.
    """

    from textwrap import TextWrapper
    wrapper = TextWrapper(width=width)
    for term, definition in deflist:
        wrapper.subsequent_indent = (tindent + dindent) * " "
        if len(term) < dindent - 1:
            wrapper.initial_indent = tindent * " "
            textToWrap = "%s%s%s" % (
                term,
                (dindent - len(term)) * " ",
                definition)
        else:
            wrapper.initial_indent = wrapper.subsequent_indent
            outfile.write("%s%s\n" % (tindent * " ", term))
            textToWrap = definition
        outfile.write("%s\n" % wrapper.fill(textToWrap))

def displayHelp():
    """Print commandline usage help text to standard output."""
    sys.stdout.write(
        "Usage: kofoto [options] command [parameters]\n"
        "\n"
        "Options:\n"
        "\n")
    printDefinitionList(optionDefinitionList, sys.stdout, 4, 27, 79)
    sys.stdout.write(
        "\n"
        "Commands:\n"
        "\n"
        "    For albums and images\n"
        "    =====================\n")
    printDefinitionList(
        albumAndImageCommandsDefinitionList, sys.stdout, 4, 27, 79)
    sys.stdout.write(
        "\n"
        "    For albums\n"
        "    ==========\n")
    printDefinitionList(albumCommandsDefinitionList, sys.stdout, 4, 27, 79)
    sys.stdout.write(
        "\n"
        "    For images\n"
        "    ==========\n")
    printDefinitionList(imageCommandsDefinitionList, sys.stdout, 4, 27, 79)
    sys.stdout.write(
        "\n"
        "    For image versions\n"
        "    ==================\n")
    printDefinitionList(
        imageversionCommandsDefinitionList, sys.stdout, 4, 27, 79)
    sys.stdout.write(
        "\n"
        "    For categories\n"
        "    ==============\n")
    printDefinitionList(categoryCommandsDefinitionList, sys.stdout, 4, 27, 79)
    sys.stdout.write(
        "\n"
        "    Miscellaneous\n"
        "    =============\n")
    printDefinitionList(
        miscellaneousCommandsDefinitionList, sys.stdout, 4, 27, 79)
    sys.stdout.write(
        "\n"
        "Parameter semantics:\n"
        "\n"
        "    Parameter         Interpretation\n"
        "    --------------------------------\n")
    printDefinitionList(
        parameterSemanticsDefinitionList, sys.stdout, 4, 18, 79)
    sys.stdout.write(
        "\n"
        "Album types:\n"
        "\n"
        "    Type              Description\n"
        "    -----------------------------\n")
    printDefinitionList(
        albumTypesDefinitionList, sys.stdout, 4, 18, 79)

def printOutput(infoString):
    """Print an informational string to standard output."""
    sys.stdout.write(infoString)
    sys.stdout.flush()

def printNotice(noticeString):
    """Print a notice to standard error."""
    sys.stderr.write("Notice: " + noticeString)

def printError(errorString):
    """Print an error to standard error."""
    sys.stderr.write("Error: " + errorString)

def printErrorAndExit(errorString):
    """Print an error and exit the program with and error code."""
    printError(errorString)
    sys.exit(1)

def sloppyGetAlbum(env, idOrTag):
    """Get an album by ID number or tag string."""
    try:
        return env.shelf.getAlbum(int(idOrTag))
    except ValueError:
        return env.shelf.getAlbumByTag(idOrTag)

def sloppyGetImage(env, idOrLocation):
    """Get an image by ID number or location."""
    try:
        return env.shelf.getImage(int(idOrLocation))
    except ValueError:
        try:
            if env.identifyByPath:
                imageversion = env.shelf.getImageVersionByLocation(
                    idOrLocation)
            else:
                imageversion = env.shelf.getImageVersionByHash(
                    computeImageHash(idOrLocation))
            return imageversion.getImage()
        except ImageVersionDoesNotExistError:
            raise ImageDoesNotExistError(idOrLocation)

def sloppyGetImageVersion(env, idOrLocation):
    """Get an image version by ID number or location."""
    try:
        return env.shelf.getImageVersion(int(idOrLocation))
    except ValueError:
        if env.identifyByPath:
            return env.shelf.getImageVersionByLocation(idOrLocation)
        else:
            return env.shelf.getImageVersionByHash(
                computeImageHash(idOrLocation))

def sloppyGetObject(env, idOrTagOrLocation):
    """Get an object version by ID number or location."""
    try:
        return sloppyGetAlbum(env, idOrTagOrLocation)
    except AlbumDoesNotExistError:
        try:
            return sloppyGetImage(env, idOrTagOrLocation)
        except (ImageDoesNotExistError, ImageVersionDoesNotExistError), x:
            raise ObjectDoesNotExistError(x)

def parseAlbumType(atype):
    """Parse an album type.

    This function takes a string representing an album type and
    returns an alternative from kofoto.shelf.AlbumType. If the album
    type does not exist, UnknownAlbumTypeError is raised.
    """
    try:
        return {
            u"plain": AlbumType.Plain,
            u"orphans": AlbumType.Orphans,
            u"search": AlbumType.Search,
            }[atype]
    except KeyError:
        raise UnknownAlbumTypeError(atype)

def parseImageVersionType(ivtype):
    """Parse an image version type.

    This function takes a string representing an image version type
    and returns an alternative from kofoto.shelf.ImageVersionType. If
    the image version type does not exist,
    UnknownImageVersionTypeError is raised. """
    try:
        return {
            u"important": ImageVersionType.Important,
            u"original": ImageVersionType.Original,
            u"other": ImageVersionType.Other,
            }[ivtype]
    except KeyError:
        raise UnknownImageVersionTypeError(ivtype)

######################################################################
### Helper classes.

class CommandlineClientEnvironment(ClientEnvironment):
    """A class encapsulating the environment useful to a command."""

    def __init__(self):
        ClientEnvironment.__init__(self)
        # Defaults:
        self.identifyByPath = False
        self.includeAll = False
        self.includeImportant = False
        self.includeOriginal = False
        self.includeOther = False
        self.includePrimary = False
        self.noAct = False
        self.useNullCharacters = False
        self.position = -1
        self.printIDs = False
        self.type = None
        self.verbose = False


    def _writeInfo(self, infoString):
        sys.stdout.write(infoString)
        sys.stdout.flush()

######################################################################
### Commands.

def cmdAdd(env, args):
    """Handler for the add command."""
    if len(args) < 2:
        raise ArgumentError
    destalbum = sloppyGetAlbum(env, args[0])
    objects = [sloppyGetObject(env, x) for x in args[1:]]
    addHelper(env, destalbum, objects)


def addHelper(env, destalbum, objects):
    """Helper function for cmdAdd."""
    oldchildren = list(destalbum.getChildren())
    if env.position == -1:
        pos = len(oldchildren)
    else:
        pos = env.position
    destalbum.setChildren(oldchildren[:pos] + objects + oldchildren[pos:])


def cmdAddCategory(env, args):
    """Handler for the add-category command."""
    if len(args) < 2:
        raise ArgumentError
    category = env.shelf.getCategoryByTag(args[0])
    for arg in args[1:]:
        sloppyGetObject(env, arg).addCategory(category)


def cmdCleanCache(env, args):
    """Handler for the clean-cache command."""
    if env.noAct:
        raise ArgumentError
    if len(args) != 0:
        raise ArgumentError
    env.imageCache.cleanup()


def cmdConnectCategory(env, args):
    """Handler for the connect-category command."""
    if len(args) != 2:
        raise ArgumentError
    parent = env.shelf.getCategoryByTag(args[0])
    child = env.shelf.getCategoryByTag(args[1])
    parent.connectChild(child)


def cmdCreateAlbum(env, args):
    """Handler for the create-album command."""
    if len(args) != 1:
        raise ArgumentError
    if env.type:
        atype = env.type
    else:
        atype = u"plain"
    env.shelf.createAlbum(args[0], parseAlbumType(atype))


def cmdCreateCategory(env, args):
    """Handler for the create-category command."""
    if len(args) != 2:
        raise ArgumentError
    env.shelf.createCategory(args[0], args[1])


def cmdDeleteAttribute(env, args):
    """Handler for the delete-attribute command."""
    if len(args) < 2:
        raise ArgumentError
    attr = args[0]
    for arg in args[1:]:
        sloppyGetObject(env, arg).deleteAttribute(attr)


def cmdDestroyAlbum(env, args):
    """Handler for the destroy-album command."""
    if len(args) == 0:
        raise ArgumentError
    for arg in args:
        env.shelf.deleteAlbum(sloppyGetAlbum(env, arg).getId())


def cmdDestroyCategory(env, args):
    """Handler for the destroy-category command."""
    if len(args) == 0:
        raise ArgumentError
    for arg in args:
        env.shelf.deleteCategory(env.shelf.getCategoryByTag(arg).getId())


def cmdDestroyImage(env, args):
    """Handler for the destroy-image command."""
    if len(args) == 0:
        raise ArgumentError
    for arg in args:
        env.shelf.deleteImage(sloppyGetImage(env, arg).getId())


def cmdDestroyImageVersion(env, args):
    """Handler for the destroy-imageversion command."""
    if len(args) == 0:
        raise ArgumentError
    for arg in args:
        env.shelf.deleteImageVersion(sloppyGetImageVersion(env, arg).getId())


def cmdDisconnectCategory(env, args):
    """Handler for the disconnect-category command."""
    if len(args) != 2:
        raise ArgumentError
    parent = env.shelf.getCategoryByTag(args[0])
    child = env.shelf.getCategoryByTag(args[1])
    parent.disconnectChild(child)


def cmdFindMissingImageVersions(env, args):
    """Handler for the find-missing-imageversions command."""
    if len(args) != 0:
        raise ArgumentError
    paths = []
    for iv in env.shelf.getAllImageVersions():
        location = iv.getLocation()
        if env.verbose:
            env.out("Checking %s ...\n" % location)
        if not os.path.exists(location):
            paths.append(location)
    for path in paths:
        env.out("%s\n" % path)


def cmdFindModifiedImageVersions(env, args):
    """Handler for the find-modified-imageversions command."""
    if len(args) != 0:
        raise ArgumentError
    paths = []
    for iv in env.shelf.getAllImageVersions():
        location = iv.getLocation()
        if env.verbose:
            env.out("Checking %s ...\n" % location)
        try:
            realId = computeImageHash(location)
            storedId = iv.getHash()
            if realId != storedId:
                paths.append(location)
        except IOError:
            pass
    for path in paths:
        env.out("%s\n" % path)


def cmdGenerate(env, args):
    """Handler for the generate command."""
    if len(args) < 2:
        raise ArgumentError
    root = sloppyGetAlbum(env, args[0])
    dest = args[1]
    subalbums = [sloppyGetAlbum(env, x) for x in args[2:]]
    if env.type:
        otype = env.type
    else:
        otype = u"woolly"
    import kofoto.generate
    try:
        generator = kofoto.generate.Generator(otype, env)
        generator.generate(root, subalbums, dest, env.gencharenc)
    except kofoto.generate.OutputTypeError, x:
        env.errexit("No such output module: %s\n" % x)


def cmdGetAttribute(env, args):
    """Handler for the get-attribute command."""
    if len(args) != 2:
        raise ArgumentError
    obj = sloppyGetObject(env, args[1])
    value = obj.getAttribute(args[0])
    if value:
        env.out(value + "\n")


def cmdGetAttributes(env, args):
    """Handler for the get-attributes command."""
    if len(args) != 1:
        raise ArgumentError
    obj = sloppyGetObject(env, args[0])
    for name in obj.getAttributeNames():
        env.out("%s: %s\n" % (name, obj.getAttribute(name)))


def cmdGetCategories(env, args):
    """Handler for the get-categories command."""
    if len(args) != 1:
        raise ArgumentError
    obj = sloppyGetObject(env, args[0])
    for category in obj.getCategories():
        env.out("%s (%s) <%s>\n" % (
            category.getDescription(),
            category.getTag(),
            category.getId()))


def cmdGetImageVersions(env, args):
    """Handler for the get-imageversions command."""
    if len(args) != 1:
        raise ArgumentError
    image = sloppyGetImage(env, args[0])
    for iv in image.getImageVersions():
        if env.printIDs:
            env.out("%s\n" % iv.getId())
        elif env.verbose:
            env.out("%s\n  %s%s\n" % (
                iv.getLocation(),
                iv.isPrimary() and "Primary, " or "",
                iv.getType()))
            if iv.getComment():
                env.out("  %s\n" % iv.getComment())
        else:
            env.out("%s\n" % iv.getLocation())


def cmdInspectPath(env, args):
    """Handler for the inspect-path command."""
    if len(args) < 1:
        raise ArgumentError
    import Image as PILImage
    for filepath in walk_files(args):
        try:
            imageversion = env.shelf.getImageVersionByHash(
                computeImageHash(filepath))
            if imageversion.getLocation() == os.path.realpath(filepath):
                env.out("[Registered]   %s\n" % filepath)
            else:
                env.out("[Moved]        %s\n" % filepath)
        except ImageVersionDoesNotExistError:
            try:
                imageversion = env.shelf.getImageVersionByLocation(filepath)
                env.out("[Modified]     %s\n" % filepath)
            except MultipleImageVersionsAtOneLocationError:
                env.out("[Multiple]     %s\n" % filepath)
            except ImageVersionDoesNotExistError:
                try:
                    PILImage.open(filepath)
                    env.out("[Unregistered] %s\n" % filepath)
#                except IOError:
                except: # Work-around for buggy PIL.
                    env.out("[Non-image]    %s\n" % filepath)


def cmdMakePrimary(env, args):
    """Handler for the make-primary command."""
    if len(args) == 0:
        raise ArgumentError
    for iv in args:
        sloppyGetImageVersion(env, iv).makePrimary()


def cmdPrintAlbums(env, args):
    """Handler for the print-albums command."""
    if len(args) > 0:
        root = sloppyGetAlbum(env, args[0])
    else:
        root = env.shelf.getRootAlbum()
    printAlbumsHelper(env, root, 0, 0, [])


def printAlbumsHelper(env, obj, position, level, visited):
    """Helper function for cmdPrintAlbums."""
    imgtmpl = "%(indent)s[I] {%(position)s} <%(id)s>\n"
    imgvertmpl = "%(indent)s[V] %(location)s {%(primary)s%(type)s} <%(id)s>\n"
    if env.verbose:
        albtmpl = "%(indent)s[A] %(name)s {%(position)s} <%(id)s> (%(type)s)\n"
    else:
        albtmpl = "%(indent)s[A] %(name)s <%(id)s> (%(type)s)\n"
    indentspaces = PRINT_ALBUMS_INDENT * " "
    if obj.isAlbum():
        tag = obj.getTag()
        env.out(albtmpl % {
            "indent": level * indentspaces,
            "name": tag,
            "position": position,
            "id": obj.getId(),
            "type": obj.getType(),
            })
        if tag in visited:
            env.out("%s[...]\n" % ((level + 1) * indentspaces))
        else:
            pos = 0
            if env.verbose:
                children = obj.getChildren()
            else:
                children = obj.getAlbumChildren()
            for child in children:
                printAlbumsHelper(
                    env,
                    child,
                    pos,
                    level + 1,
                    visited + [tag])
                pos += 1
    else:
        env.out(imgtmpl % {
            "indent": level * indentspaces,
            "position": position,
            "id": obj.getId(),
            })
        for iv in obj.getImageVersions():
            env.out(imgvertmpl % {
                "indent": (level + 1) * indentspaces,
                "id": iv.getId(),
                "location": iv.getLocation(),
                "primary": iv.isPrimary() and "Primary " or "",
                "type": iv.getType(),
                })
    if env.verbose:
        attrtmpl = "%(indent)s%(key)s: %(value)s\n"
        names = obj.getAttributeNames()
        for name in names:
            env.out(attrtmpl % {
                "indent": (level + 1) * indentspaces,
                "key": name,
                "value": obj.getAttribute(name),
                })


def cmdPrintCategories(env, args):
    """Handler for the print-categories command."""
    if len(args) != 0:
        raise ArgumentError
    for category in env.shelf.getRootCategories():
        printCategoriesHelper(env, category, 0)


def printCategoriesHelper(env, category, level):
    """Helper function for cmdPrintCategories."""
    indentspaces = PRINT_ALBUMS_INDENT * " "
    env.out("%s%s (%s) <%s>\n" % (
        level * indentspaces,
        category.getDescription(),
        category.getTag(),
        category.getId()))
    for child in category.getChildren():
        printCategoriesHelper(env, child, level + 1)


def cmdPrintStatistics(env, dummy):
    """Handler for the print-statistics command."""
    stats = env.shelf.getStatistics()
    env.out("Number of albums: %d\n" % stats["nalbums"])
    env.out("Number of categories: %d\n" % stats["ncategories"])
    env.out("Number of images: %d\n" % stats["nimages"])
    env.out("Number of image versions: %d\n" % stats["nimageversions"])


def cmdRegister(env, args):
    """Handler for the register command."""
    if len(args) < 2:
        raise ArgumentError
    destalbum = sloppyGetAlbum(env, args[0])
    registrationTimeString = unicode(time.strftime("%Y-%m-%d %H:%M:%S"))
    registerHelper(
        env,
        destalbum,
        registrationTimeString,
        args[1:])


def registerHelper(env, destalbum, registrationTimeString, paths):
    """Helper function for cmdRegister."""
    paths.sort()
    newchildren = []
    for path in paths:
        if env.verbose:
            env.out("Processing %s ...\n" % path)
        if os.path.isdir(path):
            tag = os.path.basename(path)
            if tag in DIRECTORIES_TO_IGNORE:
                if env.verbose:
                    env.out("Ignoring.\n")
                continue
            tag = makeValidTag(tag)
            while True:
                try:
                    album = env.shelf.createAlbum(tag)
                    break
                except AlbumExistsError:
                    tag += "_"
            newchildren.append(album)
            env.out("Registered directory %s as an album with tag %s\n" % (
                path,
                tag))
            registerHelper(
                env,
                album,
                registrationTimeString,
                [os.path.join(path, x) for x in os.listdir(path)])
        elif os.path.isfile(path):
            try:
                image = env.shelf.createImage()
                env.shelf.createImageVersion(
                    image, path, ImageVersionType.Original)
                image.setAttribute(u"registered", registrationTimeString)
                newchildren.append(image)
                if env.verbose:
                    env.out("Registered image: %s\n" % path)
            except NotAnImageFileError, x:
                env.out("Ignoring non-image file: %s\n" % path)
            except ImageVersionExistsError, x:
                env.err("Ignoring already registered image version: %s\n" % path)
        else:
            env.err("No such file or directory (ignored): %s\n" % path)
    addHelper(env, destalbum, newchildren)


def cmdRemove(env, args):
    """Handler for the remove command."""
    if len(args) < 2:
        raise ArgumentError
    album = sloppyGetAlbum(env, args[0])
    positions = []
    for pos in args[1:]:
        try:
            positions.append(int(pos))
        except ValueError:
            env.errexit("Bad position: %s.\n" % pos)
    positions.sort(reverse=True)
    children = list(album.getChildren())
    if not (0 <= positions[0] < len(children)):
        env.errexit("Bad position: %d.\n" % positions[0])
    for pos in positions:
        del children[pos]
    album.setChildren(children)


def cmdRemoveCategory(env, args):
    """Handler for the remove-category command."""
    if len(args) < 2:
        raise ArgumentError
    category = env.shelf.getCategoryByTag(args[0])
    for arg in args[1:]:
        sloppyGetObject(env, arg).removeCategory(category)


def cmdRenameAlbum(env, args):
    """Handler for the rename-album command."""
    if len(args) != 2:
        raise ArgumentError
    sloppyGetAlbum(env, args[0]).setTag(args[1])


def cmdRenameCategory(env, args):
    """Handler for the rename-category command."""
    if len(args) != 2:
        raise ArgumentError
    env.shelf.getCategoryByTag(args[0]).setTag(args[1])


def cmdRereadExif(env, args):
    """Handler for the reread-exif command."""
    if len(args) == 0:
        raise ArgumentError
    for iv in args:
        sloppyGetImageVersion(env, iv).importExifTags(True)


def cmdSearch(env, args):
    """Handler for the search command."""
    if len(args) != 1:
        raise ArgumentError
    parser = Parser(env.shelf)
    objects = env.shelf.search(parser.parse(args[0]))
    objects = [x for x in objects if not x.isAlbum()]
    ivs = []
    for o in objects:
        for iv in o.getImageVersions():
            ivs.append(iv)
    if env.printIDs:
        ids = set()
        for iv in ivs:
            ids.add(iv.getImage().getId())
        output = [str(x) for x in ids]
    else:
        output = []
        for iv in ivs:
            t = iv.getType()
            if (env.includeAll or
                (env.includeImportant and t == ImageVersionType.Important) or
                (env.includeOriginal and t == ImageVersionType.Original) or
                (env.includeOther and t == ImageVersionType.Other) or
                (env.includePrimary and iv.isPrimary())):
                output.append(iv.getLocation())
        output.sort()
    if output:
        if env.useNullCharacters:
            terminator = u"\0"
        else:
            terminator = u"\n"
        env.out(u"%s%s" % (terminator.join(output), terminator))


def cmdSetAttribute(env, args):
    """Handler for the set-attribute command."""
    if len(args) < 3:
        raise ArgumentError
    attr = args[0]
    value = args[1]
    for arg in args[2:]:
        sloppyGetObject(env, arg).setAttribute(attr, value)


def cmdSetCategoryDescription(env, args):
    """Handler for the set-category-description command."""
    if len(args) != 2:
        raise ArgumentError
    env.shelf.getCategoryByTag(args[0]).setDescription(args[1])


def cmdSetImageVersionComment(env, args):
    """Handler for the set-imageversion-comment command."""
    if len(args) < 2:
        raise ArgumentError
    comment = args[0]
    for iv in args[1:]:
        sloppyGetImageVersion(env, iv).setComment(comment)


def cmdSetImageVersionImage(env, args):
    """Handler for the set-imageversion-image command."""
    if len(args) < 2:
        raise ArgumentError
    image = sloppyGetImage(env, args[0])
    for iv in args[1:]:
        sloppyGetImageVersion(env, iv).setImage(image)


def cmdSetImageVersionType(env, args):
    """Handler for the set-imageversion-type command."""
    if len(args) < 2:
        raise ArgumentError
    ivtype = parseImageVersionType(args[0])
    for iv in args[1:]:
        sloppyGetImageVersion(env, iv).setType(ivtype)


def cmdSortAlbum(env, args):
    """Handler for the sort-album command."""
    if not 1 <= len(args) <= 2:
        raise ArgumentError
    if len(args) == 2:
        attr = args[1]
    else:
        attr = u"captured"
    album = sloppyGetAlbum(env, args[0])
    children = list(album.getChildren())
    children.sort(key=lambda x: x.getAttribute(attr))
    album.setChildren(children)


def cmdUpdateContents(env, args):
    """Handler for the update-contents command."""
    if len(args) < 1:
        raise ArgumentError
    for filepath in walk_files(args):
        try:
            imageversion = env.shelf.getImageVersionByLocation(filepath)
            oldhash = imageversion.getHash()
            imageversion.contentChanged()
            if imageversion.getHash() != oldhash:
                env.out("New checksum: %s\n" % filepath)
            else:
                if env.verbose:
                    env.out(
                        "Same checksum as before: %s\n" % filepath)
        except ImageVersionDoesNotExistError:
            if env.verbose:
                env.out("Unregistered image/file: %s\n" % filepath)
        except MultipleImageVersionsAtOneLocationError:
            env.errexit(
                "Multiple known image versions at this location: %s\n" % (
                filepath))


def cmdUpdateLocations(env, args):
    """Handler for the update-locations command."""
    if len(args) < 1:
        raise ArgumentError
    for filepath in walk_files(args):
        try:
            imageversion = env.shelf.getImageVersionByHash(
                computeImageHash(filepath))
            oldlocation = imageversion.getLocation()
            if oldlocation != os.path.realpath(filepath):
                imageversion.locationChanged(filepath)
                env.out("New location: %s --> %s\n" % (
                    oldlocation,
                    imageversion.getLocation()))
            else:
                if env.verbose:
                    env.out(
                        "Same location as before: %s\n" % filepath)
        except IOError, x:
            if env.verbose:
                env.out("Failed to read: %s (%s)\n" % (
                    filepath,
                    x))
        except ImageVersionDoesNotExistError:
            if env.verbose:
                env.out("Unregistered image/file: %s\n" % filepath)


commandTable = {
    "add": cmdAdd,
    "add-category": cmdAddCategory,
    "clean-cache": cmdCleanCache,
    "connect-category": cmdConnectCategory,
    "create-album": cmdCreateAlbum,
    "create-category": cmdCreateCategory,
    "delete-attribute": cmdDeleteAttribute,
    "destroy-album": cmdDestroyAlbum,
    "destroy-category": cmdDestroyCategory,
    "destroy-image": cmdDestroyImage,
    "destroy-imageversion": cmdDestroyImageVersion,
    "disconnect-category": cmdDisconnectCategory,
    "find-missing-imageversions": cmdFindMissingImageVersions,
    "find-modified-imageversions": cmdFindModifiedImageVersions,
    "generate": cmdGenerate,
    "get-attribute": cmdGetAttribute,
    "get-attributes": cmdGetAttributes,
    "get-categories": cmdGetCategories,
    "get-imageversions": cmdGetImageVersions,
    "inspect-path": cmdInspectPath,
    "make-primary": cmdMakePrimary,
    "print-albums": cmdPrintAlbums,
    "print-categories": cmdPrintCategories,
    "print-statistics": cmdPrintStatistics,
    "register": cmdRegister,
    "remove": cmdRemove,
    "remove-category": cmdRemoveCategory,
    "rename-album": cmdRenameAlbum,
    "rename-category": cmdRenameCategory,
    "reread-exif": cmdRereadExif,
    "search": cmdSearch,
    "set-attribute": cmdSetAttribute,
    "set-category-description": cmdSetCategoryDescription,
    "set-imageversion-comment": cmdSetImageVersionComment,
    "set-imageversion-image": cmdSetImageVersionImage,
    "set-imageversion-type": cmdSetImageVersionType,
    "sort-album": cmdSortAlbum,
    "update-contents": cmdUpdateContents,
    "update-locations": cmdUpdateLocations,
}

######################################################################
### Main

def main(argv):
    """Run the program.

    Arguments:

    argv -- A list of arguments.
    """
    env = CommandlineClientEnvironment()

    argv = [x.decode(env.filesystemEncoding) for x in argv]

    sys.stdin = codecs.getreader(get_file_encoding(sys.stdin))(sys.stdin)
    sys.stdout = codecs.getwriter(get_file_encoding(sys.stdout))(sys.stdout)
    sys.stderr = codecs.getwriter(get_file_encoding(sys.stderr))(sys.stderr)

    try:
        optlist, args = getopt.gnu_getopt(
            argv[1:],
            "0ht:v",
            ["configfile=",
             "database=",
             "gencharenc=",
             "help",
             "identify-by-hash",
             "identify-by-path",
             "ids",
             "include-all",
             "include-important",
             "include-original",
             "include-other",
             "include-primary",
             "no-act",
             "null",
             "position=",
             "type=",
             "verbose",
             "version"])
    except getopt.GetoptError:
        printErrorAndExit("Unknown option. See \"kofoto --help\" for help.\n")

    # Other defaults:
    shelfLocation = None
    configFileLocation = None
    genCharEnc = "utf-8"

    for opt, optarg in optlist:
        if opt == "--configfile":
            configFileLocation = expanduser(optarg)
        elif opt == "--database":
            shelfLocation = optarg
        elif opt == "--gencharenc":
            genCharEnc = str(optarg)
        elif opt in ("-h", "--help"):
            displayHelp()
            sys.exit(0)
        elif opt == "--identify-by-hash":
            env.identifyByPath = False
        elif opt == "--identify-by-path":
            env.identifyByPath = True
        elif opt == "--ids":
            env.printIDs = True
        elif opt == "--include-all":
            env.includeAll = True
        elif opt == "--include-important":
            env.includeImportant = True
        elif opt == "--include-original":
            env.includeOriginal = True
        elif opt == "--include-other":
            env.includeOther = True
        elif opt == "--include-primary":
            env.includePrimary = True
        elif opt == "--no-act":
            printNotice(
                "no-act: No changes will be commited to the database!\n")
            env.noAct = True
        elif opt in ("-0", "--null"):
            env.useNullCharacters = True
        elif opt == "--position":
            if optarg == "last":
                env.position = -1
            else:
                try:
                    env.position = int(optarg)
                except ValueError:
                    printErrorAndExit("Invalid position: \"%s\"\n" % optarg)
        elif opt in ("-t", "--type"):
            env.type = optarg
        elif opt in ("-v", "--verbose"):
            env.verbose = True
        elif opt == "--version":
            sys.stdout.write("%s\n" % env.version)
            sys.exit(0)

    if not (env.includeAll or env.includeImportant or env.includeOriginal
            or env.includeOther or env.includePrimary):
        env.includePrimary = True

    if len(args) == 0:
        printErrorAndExit(
            "No command given. See \"kofoto --help\" for help.\n")

    try:
        env.setup(configFileLocation, shelfLocation)
    except ClientEnvironmentError, e:
        printErrorAndExit(e[0])

    if not commandTable.has_key(args[0]):
        printErrorAndExit(
            "Unknown command \"%s\". See \"kofoto --help\" for help.\n" % (
            args[0]))

    try:
        if env.shelf.isUpgradable():
            printNotice(
                "Upgrading %s to new database format...\n" % env.shelfLocation)
            if not env.shelf.tryUpgrade():
                printErrorAndExit(
                    "Failed to upgrade metadata database format.\n")
        env.shelf.begin()
    except ShelfNotFoundError, x:
        printErrorAndExit("Could not open metadata database \"%s\".\n" % (
            env.shelfLocation))
    except ShelfLockedError, x:
        printErrorAndExit(
            "Could not open metadata database \"%s\".\n" % env.shelfLocation +
            "Another process is locking it.\n")
    except UnsupportedShelfError, filename:
        printErrorAndExit(
            "Could not read metadata database file %s (too new database"
            " format?).\n" % filename)
    try:
        env.gencharenc = genCharEnc
        env.out = printOutput
        env.err = printError
        env.errexit = printErrorAndExit
        env.thumbnailsizelimit = env.config.getcoordlist(
            "album generation", "thumbnail_size_limit")[0]
        env.defaultsizelimit = env.config.getcoordlist(
            "album generation", "default_image_size_limit")[0]

        imgsizesval = env.config.getcoordlist(
            "album generation", "other_image_size_limits")
        imgsizesset = set(imgsizesval) # Get rid of duplicates.
        defaultlimit = env.config.getcoordlist(
            "album generation", "default_image_size_limit")[0]
        imgsizesset.add(defaultlimit)
        imgsizes = list(imgsizesset)
        imgsizes.sort(lambda x, y: cmp(x[0] * x[1], y[0] * y[1]))
        env.imagesizelimits = imgsizes

        commandTable[args[0]](env, args[1:])
        if env.noAct:
            env.shelf.rollback()
            printOutput(
                "no-act: All changes to the database have been revoked!\n")
        else:
            env.shelf.commit()
        sys.exit(0)
    except ArgumentError:
        printErrorAndExit(
            "Bad arguments to command. See \"kofoto --help\" for help.\n")
    except UndeletableAlbumError, x:
        printError("Undeletable album: \"%s\".\n" % x.args[0])
    except BadAlbumTagError, x:
        printError("Bad album tag: \"%s\".\n" % x.args[0])
    except AlbumExistsError, x:
        printError("Album already exists: \"%s\".\n" % x.args[0])
    except ImageDoesNotExistError, x:
        printError("Image does not exist: \"%s\".\n" % x.args[0])
    except AlbumDoesNotExistError, x:
        printError("Album does not exist: \"%s\".\n" % x.args[0])
    except ObjectDoesNotExistError, x:
        printError("Object does not exist: \"%s\".\n" % x.args[0])
    except UnknownAlbumTypeError, x:
        printError("Unknown album type: \"%s\".\n" % x.args[0])
    except UnsettableChildrenError, x:
        printError(
            "Cannot modify children of \"%s\" (children are created"
            " virtually).\n" % x.args[0])
    except CategoryExistsError, x:
        printError("Category already exists: \"%s\".\n" % x.args[0])
    except CategoryDoesNotExistError, x:
        printError("Category does not exist: \"%s\".\n" % x.args[0])
    except BadCategoryTagError, x:
        printError("Bad category tag: %s.\n" % x.args[0])
    except CategoryPresentError, x:
        printError("Object %s is already associated with category %s.\n" % (
            x.args[0], x.args[1]))
    except CategoriesAlreadyConnectedError, x:
        printError("Categories %s and %s are already connected.\n" % (
            x.args[0], x.args[1]))
    except CategoryLoopError, x:
        printError(
            "Connecting %s to %s would make a loop in the categories.\n" % (
            x.args[0], x.args[1]))
    except UnterminatedStringError, x:
        printError(
            "While scanning search expression: unterminated string starting at"
            " character %d.\n" % x.args[0])
    except BadTokenError, x:
        printError(
            "While scanning search expression: bad token starting at character"
            " %d.\n" % x.args[0])
    except ParseError, x:
        printError(
            "While parsing search expression: %s.\n" % x.args[0])
    except UnknownImageVersionTypeError, x:
        printError("Unknown image version type: \"%s\".\n" % x.args[0])
    except ExifImportError, x:
        printError("Failed to import EXIF information from \"%s\".\n" % (
            x.args[0]))
    except KeyboardInterrupt:
        printOutput("Interrupted.\n")
    except IOError, e:
        if e.filename:
            errstr = "%s: \"%s\"" % (e.strerror, e.filename)
        else:
            errstr = e.strerror
        printError("%s.\n" % errstr)
    env.shelf.rollback()
    sys.exit(1)
