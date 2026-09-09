from matplotlib import pyplot as plt
import pyworkflow.viewer as pwviewer
from isonet2.protocols.protocol_training import ProtIsonet2Training
from pwem.viewers import ImageView



class Isonet2CurvesViewer(pwviewer.Viewer):
    _label = 'Learning Curves Viewer'
    _targets = [ProtIsonet2Training]

    def _visualize(self, obj, **kwargs):
        view = Isonet2ImageView(self.protocol._getModelOutDir('loss_full.png'))
        view._tkParent = self.getTkRoot()
        return [view]

class Isonet2ImageView(ImageView):

    def show(self):
        image_file = self.getImagePath()
        plt.figure(num='Isonet2 Learning Curves')
        image = plt.imread(image_file)
        plt.imshow(image)
        plt.axis('off')
        plt.tight_layout()  # Decrease the padding
        plt.show()

