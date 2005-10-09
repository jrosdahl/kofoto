"""Shelf-related exceptions."""

__all__ = [
    "AlbumDoesNotExistError",
    "AlbumExistsError",
    "BadAlbumTagError",
    "BadCategoryTagError",
    "CategoriesAlreadyConnectedError",
    "CategoryDoesNotExistError",
    "CategoryExistsError",
    "CategoryLoopError",
    "CategoryPresentError",
    "ExifImportError",
    "FailedWritingError",
    "ImageDoesNotExistError",
    "ImageVersionDoesNotExistError",
    "ImageVersionExistsError",
    "MultipleImageVersionsAtOneLocationError",
    "NotAnImageFileError",
    "ObjectDoesNotExistError",
    "ShelfLockedError",
    "ShelfNotFoundError",
    "UndeletableAlbumError",
    "UnknownAlbumTypeError",
    "UnknownImageVersionTypeError",
    "UnsettableChildrenError",
    "UnsupportedShelfError",
]

from kofoto.common import KofotoError

class ObjectDoesNotExistError(KofotoError):
    """Object does not exist in the album."""

class AlbumDoesNotExistError(ObjectDoesNotExistError):
    """Album does not exist in the album."""

class AlbumExistsError(KofotoError):
    """Album already exists in the shelf."""

class BadAlbumTagError(KofotoError):
    """Bad album tag."""

class BadCategoryTagError(KofotoError):
    """Bad category tag."""

class CategoriesAlreadyConnectedError(KofotoError):
    """The categories are already connected."""

class CategoryDoesNotExistError(KofotoError):
    """Category does not exist."""

class CategoryExistsError(KofotoError):
    """Category already exists."""

class CategoryLoopError(KofotoError):
    """Connecting the categories would create a loop in the category DAG."""

class CategoryPresentError(KofotoError):
    """The object is already associated with this category."""

class ExifImportError(KofotoError):
    """Failed to import EXIF information."""

class FailedWritingError(KofotoError):
    """Kofoto shelf already exists."""

class ImageDoesNotExistError(KofotoError):
    """Image does not exist."""

class ImageVersionDoesNotExistError(KofotoError):
    """Image version does not exist."""

class ImageVersionExistsError(KofotoError):
    """Image version already exists in the shelf."""

class MultipleImageVersionsAtOneLocationError(KofotoError):
    """Failed to identify image version by location since the location
    isn't unique."""

class NotAnImageFileError(KofotoError):
    """Could not recognise file as an image file."""

class SearchExpressionParseError(KofotoError):
    """Could not parse search expression."""

class ShelfLockedError(KofotoError):
    """The shelf is locked by another process."""

class ShelfNotFoundError(KofotoError):
    """Kofoto shelf not found."""

class UndeletableAlbumError(KofotoError):
    """Album is not deletable."""

class UnknownAlbumTypeError(KofotoError):
    """The album type is unknown."""

class UnknownImageVersionTypeError(KofotoError):
    """The image version type is unknown."""

class UnsettableChildrenError(KofotoError):
    """The album is magic and doesn't have any explicit children."""

class UnsupportedShelfError(KofotoError):
    """Unsupported shelf database format."""
