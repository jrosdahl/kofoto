from kofoto.common import KofotoError

class OutputTypeError(KofotoError):
    """No such output type."""
    pass


class Generator:
    def __init__(self, outputtype, env):
        self.env = env
        try:
            outputmodule = getattr(
                __import__("kofoto.output.%s" % outputtype).output,
                outputtype)
        except ImportError:
            raise OutputTypeError, outputtype
        self.ogclass = outputmodule.OutputGenerator


    def generate(self, root, dest):
        og = self.ogclass(self.env)
        og.generate(root, dest)
