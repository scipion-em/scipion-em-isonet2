# -*- coding: utf-8 -*-
# **************************************************************************
# *
# * Authors:     Scipion Team
# *
# * National Center of Biotechnology, CSIC, Spain
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************
import logging


from isonet2.constants import PREPARE_DATA_PROT, CTF_NONE, CTF_PHASE_ONLY, CTF_WIENER, CTF_NETWORK
from isonet2.protocols.protocol_base import ProtIsonet2Base
from pyworkflow import BETA
from pyworkflow.protocol import PointerParam, GPU_LIST, StringParam, EnumParam
from pyworkflow.utils import Message

logger = logging.getLogger(__name__)


# class Outputobjects(Enum):
#     model = Isonet2Model


class ProtIsonet2Training(ProtIsonet2Base):
    """Denoise for quicker noise-to-noise (n2n) training workflows for preliminary
    tomogram testing and mask generation."""

    _label = 'Isonet2 training (denoising)'
    _devStatus = BETA

    # _possibleOutputs = Outputobjects

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # --------------------------- DEFINE param functions ----------------------
    def _defineParams(self, form):
        form.addSection(label=Message.LABEL_INPUT)
        form.addParam(PREPARE_DATA_PROT, PointerParam,
                      pointerClass='ProtIsonet2PrepareData',
                      important=True,
                      label='Isonet prepare data protocol')

        form.addParam('pretrained_model', PointerParam,
                      pointerClass='ProtIsonet2PretrainedModel',
                      label='Isonet pretrained model',
                      allowsNull=True,
                      help='Pretrained model to continue training. Previous method, arch, cube_size, '
                           'CTF_mode, and metrics will be loaded.'
                      )

        form.addSection(label='CTF Mode')
        form.addParam('CTF_mode',EnumParam,
                      label='CTF mode',
                      choices=[CTF_NONE,CTF_PHASE_ONLY,CTF_WIENER,CTF_NETWORK],
                      defaut=CTF_NONE,
                      display=EnumParam.DISPLAY_HLIST,
                      help='CTF handling mode: "None", "phase_only", "wiener", or "network".'
                      )



        form.addHidden(GPU_LIST, StringParam,
                       default='0',
                       label="Choose GPU IDs",
                       help="")
