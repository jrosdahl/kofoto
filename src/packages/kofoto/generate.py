"""Implementation of the Generator class."""

__all__ = ["Generator", "OutputTypeError"]

from kofoto.common import KofotoError

class OutputTypeError(KofotoError):
    """No such output type."""
    pass


class Generator:
    """HTML output generator."""

    def __init__(self, outputtype, env):
        """Constructor.

        Arguments:

        outputtype -- Output module name.
        env        -- Client environment instance.
        """

        self.env = env
        try:
            outputmodule = getattr(
                __import__("kofoto.output.%s" %
                           outputtype.encode(env.codeset)).output,
                outputtype)
        except ImportError:
            raise OutputTypeError, outputtype
        self.ogclass = outputmodule.OutputGenerator


    def generate(self, root, subalbums, dest, character_encoding):
        """Generate HTML.

        Arguments:

        root      -- Album to consider the root album.
        subalbums -- A list of subalbums to generate. If empty, all
                     subalbums are generated.
        dest      -- Directory in which the generated HTML files should be
                     put.
        character_encoding -- Codeset to use in HTML files.
        """
        og = self.ogclass(self.env, character_encoding)
        og.generate(root, subalbums, dest)
