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

from isonet2.constants import PREPARE_DATA_PROT
from isonet2.protocols.protocol_base import ProtIsonet2Base
from pyworkflow import BETA
from pyworkflow.protocol import PointerParam, GPU_LIST, StringParam, BooleanParam, FloatParam
from pyworkflow.utils import Message

logger = logging.getLogger(__name__)



class ProtIsonet2Predict(ProtIsonet2Base):
    """Apply a trained IsoNet model to tomograms to produce denoised or missing-wedge–corrected volumes.
    Prediction utilizes the model's saved cube size and CTF handling options, but allows for runtime adjustments."""

    _label = 'predict'
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
                      label='Isonet2 Prepare data protocol.'
                      )
        form.addParam('model', PointerParam,
                      pointerClass='Isonet2Model',
                      important=True,
                      label='Isonet2 Model',
                      allowsNull=False,
                      help='Select a trained Isonet2 model.'
                      )
        form.addParam('missingWedge_mask', BooleanParam,
                      label='Missing wedge mask',
                      default=True,
                      help='Build and apply a missing-wedge mask to cubic inputs before prediction.'
                      )
        form.addParam('isCTFflipped', BooleanParam,
                      label='Is CTF flipped?',
                      default=False,
                      help='Whether input tomograms are phase flipped.'
                           'Set to "Yes" if the input tomograms have been phase flipped.'
                      )
        form.addParam('padding_factor',FloatParam,
                      label='Padding factor',
                      default=1.5,
                      help='Cubic padding factor used during tiling to reduce edge effects; '
                           'larger padding reduces seams but increases computation.'
                      )
        form.addParam('tomo_idx', StringParam,
                      label='Tomogram index',
                      default='None',
                      help='Process a subset of STAR entries by index.'
                      )
        form.addHidden(GPU_LIST, StringParam,
                       default='0',
                       label="Choose GPU IDs",
                       help=""
                       )