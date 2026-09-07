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
import traceback
from enum import Enum

from isonet2 import Plugin
from isonet2.constants import PREPARE_DATA_PROT
from isonet2.objects import Isonet2Model
from isonet2.protocols.protocol_base import ProtIsonet2Base
from pyworkflow import BETA
from pyworkflow.protocol import PointerParam, GPU_LIST, StringParam, BooleanParam, FloatParam, GT
from pyworkflow.utils import Message, makePath, cyanStr, redStr
from tomo.objects import SetOfTomograms

logger = logging.getLogger(__name__)

class Outputobjects(Enum):
    tomograms = SetOfTomograms


class ProtIsonet2Predict(ProtIsonet2Base):
    """Apply a trained IsoNet model to tomograms to produce denoised or missing-wedge–corrected volumes.
    Prediction utilizes the model's saved cube size and CTF handling options, but allows for runtime adjustments."""

    _label = 'predict'
    _devStatus = BETA
    _possibleOutputs = Outputobjects


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
                      validators=[GT(0)],
                      help='Cubic padding factor used during tiling to reduce edge effects; '
                           'larger padding reduces seams but increases computation.'
                      )
        form.addParam('tomo_idx', StringParam,
                      label='Tomogram index',
                      default='None',
                      help='Process a subset of STAR entries by index.'
                           '(e.g., "1,2,4" or "5-10,15,16")'
                      )
        form.addHidden(GPU_LIST, StringParam,
                       default='0',
                       label="Choose GPU IDs",
                       help=""
                       )

    # --------------------------- INSERT steps functions ----------------------
    def _insertAllSteps(self):

        self._initialize()
        self._insertFunctionStep(self.predictStep, needsGPU=True)
        self._insertFunctionStep(self.createOutputStep, needsGPU=False)

    # -------------------------- STEPS functions ------------------------------
    def _initialize(self):
        makePath(self._getModelOutDir())

    def predictStep(self):
        logger.info(cyanStr(f' Predict step...'))

        try:
            args = self._generateArguments()
            Plugin.runIsonet2(self, args, useGpu=True)
        except Exception as e:
            logger.error(redStr(f'Predict step failed with the exception -> {e}'))
            logger.error(traceback.format_exc())

    def createOutputStep(self):
        pass



    # -------------------------- UTILS functions ------------------------------
    def _getModelOutDir(self):
        return self._getExtraPath('predict')

    def _getModelPath(self, model:Isonet2Model):
        return model.getPath()

    def _generateArguments(self) -> str:
        starFile = self._getStarFile()
        model = self.model.get()
        modelPath = self._getModelPath(model)
        output_dir = self._getModelOutDir()

        cmd =[
            'predict',
            f'--star_file {starFile}',
            f'--model {modelPath}',
            '--apply_mw_x1',
            f'--isCTFflipped',
            f'--output_dir {output_dir}',
            f'--padding_factor {self.padding_factor.get()}',
            f'tomo_idx {self.tomo_idx.get()}'
            ]

        return ' '.join(cmd)




