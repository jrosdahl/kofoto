__all__ = ["Generator", "OutputTypeError"]

from kofoto.common import KofotoError

class OutputTypeError(KofotoError):
    """No such output type."""
    pass


class Generator:
    def __init__(self, outputtype, env):
        self.env = env
        try:
            outputmodule = getattr(
                __import__("kofoto.output.%s" %
                           outputtype.encode(env.codeset)).output,
                outputtype)
        except ImportError:
            raise OutputTypeError, outputtype
        self.ogclass = outputmodule.OutputGenerator


    def generate(self, root, dest, character_encoding):
        og = self.ogclass(self.env, character_encoding)
        og.generate(root, dest)
