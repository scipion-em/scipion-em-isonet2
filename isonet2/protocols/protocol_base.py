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
from typing import Union, Optional

from isonet2.constants import PREPARE_DATA_PROT
from pwem.protocols import EMProtocol
from pyworkflow.object import Pointer
from tomo.objects import SetOfTomograms, SetOfTiltSeries,SetOfCTFTomoSeries


class ProtIsonet2Base(EMProtocol):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _getFormAttrib(self, attribName: str, returnPointer: bool = False) -> Optional[Union[SetOfTiltSeries,
    SetOfTomograms, SetOfCTFTomoSeries, Pointer]]:
        inTsPointer = getattr(self, attribName, None)
        if not inTsPointer:
            return None
        else:
            return inTsPointer if returnPointer else inTsPointer.get()

    def _getStarFile(self):
        protPrepare = self._getFormAttrib(PREPARE_DATA_PROT)