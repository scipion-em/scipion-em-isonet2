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
from isonet2.constants import PREPARE_DATA_PROT, PREDICT_PROT
from isonet2.protocols.protocol_base import ProtIsonet2Base
from pyworkflow import BETA
from pyworkflow.protocol import PointerParam, ElementGroup, IntParam, GT, FloatParam, StringParam
from pyworkflow.utils import Message, redStr, cyanStr
from tomo.objects import SetOfTomoMasks

logger = logging.getLogger(__name__)

class Outputobjects(Enum):
    masks = SetOfTomoMasks

class ProtIsonet2MakeMask(ProtIsonet2Base):
    """Generate masks to prioritize regions of interest.
    Masks improve sampling efficiency and training stability."""

    _label = 'Isonet2 make mask'
    _devStatus = BETA

    # _possibleOutputs = Outputobjects

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # --------------------------- DEFINE param functions -----------------
    def _defineParams(self, form):
        form.addSection(label=Message.LABEL_INPUT)
        form.addParam(PREDICT_PROT, PointerParam,
                      pointerClass='ProtIsonet2Predict',
                      important=True,
                      label='Isonet2 Predict Protocol'
                      )
        form.addParam('tomo_idx', StringParam,
                      label='Tomogram index',
                      allowsNull=True,
                      help='If set, process only the tomograms listed by these indices '
                           '(e.g., "1,2,4" or "5-10,15,16").'
                      )

        group = form.addGroup('Mask Generation')
        group.addParam('density_percentage', IntParam,
                       label='Density percentage',
                       default=50,
                       validators=[GT(0)],
                       help='Percentage of voxels retained based on local density ranking; '
                            'lower values create stricter masks (keep fewer voxels)'
                       )
        group.addParam('patch_size', IntParam,
                       label='Patch size',
                       default=4,
                       validators=[GT(0)],
                       help='Local patch size used for max/std local filters; '
                            'larger values smooth detection of specimen regions; default works for typical pixel sizes'
                       )
        group.addParam('std_percentage', IntParam,
                       label='Std percentage',
                       default=50,
                       validators=[GT(0)],
                       help='Percentage retained based on local standard-deviation ranking; '
                            'lower values emphasize textured regions'
                       )
        group.addParam('z_crop', FloatParam,
                       label='Z crop',
                       default=0.2,
                       validators=[GT(0)],
                       help='Fraction of tomogram Z to crop from both ends; '
                            'masks out top and bottom 10% each when set to 0.2.'
                            ' Use to avoid sampling low-quality reconstruction edges.'
                       )

    # --------------------------- INSERT steps functions ----------------------
    def _insertAllSteps(self):
        self._initialize()

        self._insertFunctionStep(self.makeMaskStep, needsGPU=False)
        self._insertFunctionStep(self.createOutputStep, needsGPU=False)

    # -------------------------- STEPS functions ------------------------------
    def _initialize(self):
        self._copyStar()

    def makeMaskStep(self):
        logger.info(cyanStr(f' Make Mask step...'))

        try:
            args = self._generateArguments()
            Plugin.runIsonet2(self, args, useGpu=True)
        except Exception as e:
            logger.error(redStr(f'Make mask failed with the exception -> {e}'))
            logger.error(traceback.format_exc())

    def createOutputStep(self):
        pass

    def _generateArguments(self) -> str:
        output_dir = self._getExtraPath()
        starFile = self._newStarPath()


        cmd = [
            'make_mask',
            f'--star_file {starFile}',
            f'--output_dir {output_dir}',
            f'--input_column "rlnDenoisedTomoName"',
            f'--patch_size {self.patch_size.get()}',
            f'--density_percentage {self.density_percentage.get()}',
            f'--std_percentage {self.std_percentage.get()}',
            f'--z_crop {self.z_crop.get()}',
            f'--tomo_idx {self.tomo_idx.get()}'

        ]
        return ' '.join(cmd)

    def _createOutputSet(self) -> SetOfTomoMasks:
        pass







