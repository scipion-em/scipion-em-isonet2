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
from typing import Union, List
from isonet2.constants import EVEN_DIR, ODD_DIR, MASKS_DIR, TOMOGRAMS_STAR
from pwem.protocols import EMProtocol
from tomo.objects import SetOfTomograms, SetOfTiltSeries


class ProtIsonet2Base(EMProtocol):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def runPrepareStarFile(self) -> None:
        pass

    def _genPrepareStarCmd(self,
                           inTomos: SetOfTomograms,
                           inTsSet: SetOfTiltSeries,
                           zeroTiltDefocus: Union[float, List[float]]) -> str:
        apix = inTomos.getSamplingRate()
        acq = inTsSet.getAcquisition()
        # TODO: check where to get the zeroTiltDefocus from
        cmd = [
            f'--even {self._getEvenDir()}',
            f'--odd {self._getOddDir()}',
            f'--star_name {self._getTomosStarName()}',
            f'--pixel_size {apix}',
            f'--defocus {zeroTiltDefocus}',
            f'--cs {acq.getSphericalAberration()}',
            f'--voltage {acq.getVoltage()}',
            f'--ac {acq.getAmplitudeContrast()}',
            f'--tilt_min {acq.getAngleMin()}',
            f'--tilt_max {acq.getAngleMax()}',
            '--create_average True',
        ]
        # TODO: add mask dir if introduced
        return ' '.join(cmd)

    def _getOddDir(self) -> str:
        return self._getTmpPath(ODD_DIR)

    def _getEvenDir(self) -> str:
        return self._getTmpPath(EVEN_DIR)

    def _getMaskDir(self) -> str:
        return self._getTmpPath(MASKS_DIR)

    def _getTomosStarName(self) -> str:
        return self._getTmpPath(TOMOGRAMS_STAR)

