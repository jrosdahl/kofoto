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

