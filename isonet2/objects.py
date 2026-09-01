from pwem import EMObject
import pyworkflow.object as pwobj

class Isonet2Model(EMObject):
    def __init__(self, model_file=None, **kwargs):
        EMObject.__init__(self, **kwargs)
        self._model_file = pwobj.String(model_file)

    def getPath(self):
        return self._model_file.get()

    def __str__(self):
        return "Isonet2 Model (path=%s)" % self.getPath()