class CachedObject:
    def __init__(self, constructor, args=()):
        self.constructor = constructor
        self.args = args

    def get(self):
        if not hasattr(self, "object"):
            self.object = self.constructor(*self.args)
        return self.object

    def invalidate(self):
        if hasattr(self, "object"):
            del self.object
