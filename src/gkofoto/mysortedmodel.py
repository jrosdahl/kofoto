import gtk

class MySortedModel(gtk.TreeModelSort):

    def __init__(self, model):
        gtk.TreeModelSort.__init__(self, model)
        self._model = model

    def __getitem__(self, path):
        child_path = self.convert_path_to_child_path(path)
        if child_path:
            return self._model[child_path]
        else:
            raise IndexError

    def set_value(self, iter, column, value):
        childIter = self._model.get_iter_first()
        self.convert_iter_to_child_iter(childIter, iter)
        self._model.set_value(childIter, column, value)

    # Workaround until http://bugzilla.gnome.org/show_bug.cgi?id=121633 is solved.
    def get_iter_first(self):
        if len(self) > 0:
            return gtk.TreeModelSort.get_iter_first(self)
        else:
            return None

    # Workaround until http://bugzilla.gnome.org/show_bug.cgi?id=121633 is solved.
    def __iter__(self):
        if len(self._model) > 0:
            return gtk.TreeModelSort.__iter__(self)
        else:
            return self._model.__iter__()
