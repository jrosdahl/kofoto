import gtk

class MySortedModel(gtk.TreeModelSort):

    def __init__(self, model):
        gtk.TreeModelSort.__init__(self, model)
        self._model = model
        #self._model.connect("row_changed", self._child_model_changed)
    
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
