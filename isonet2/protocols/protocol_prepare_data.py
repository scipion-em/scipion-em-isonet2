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
from os.path import join, exists
from typing import List, Optional
from isonet2 import Plugin
from isonet2.constants import IN_TOMOS, IN_CTF_SET, IN_TS_SET, TOMO_MASKS, MASK_SUFFIX, ODD_SUFFIX, MRC_EXT, \
    EVEN_SUFFIX, ODD_DIR, EVEN_DIR, MASKS_DIR, TOMOGRAMS_STAR
from isonet2.protocols.protocol_base import ProtIsonet2Base
from pyworkflow import BETA
from pyworkflow.object import String
from pyworkflow.protocol import PointerParam
from pyworkflow.utils import Message, cyanStr, yellowStr, makePath, redStr
from tomo.objects import TiltSeries, CTFTomoSeries, SetOfTomoMasks, TomoAcquisition
from tomo.utils import getTsIdsIntersection, getTsIdsDicts, check_sr_and_size, convertOrLink

logger = logging.getLogger(__name__)


class ProtIsonet2PrepareData(ProtIsonet2Base):
    """Generate the data in the format specified by IsoNet2."""

    _label = 'prepare data'
    _devStatus = BETA

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.samplingRate = -1
        self.tsDict = {}
        self.tomoDict = {}
        self.ctfDict = {}
        self.tomoMaskDict = {}
        self.failedTsIds = []
        self._tomoFile = String()

    # --------------------------- DEFINE param functions ----------------------
    def _defineParams(self, form):
        form.addSection(label=Message.LABEL_INPUT)
        form.addParam(IN_TOMOS, PointerParam,
                      pointerClass='SetOfTomograms',
                      important=True,
                      label='Tomograms')

        form.addParam(IN_CTF_SET, PointerParam,
                      pointerClass='SetOfCTFTomoSeries',
                      label="CTF tomo series",
                      important=True)

        form.addParam(IN_TS_SET, PointerParam,
                      pointerClass='SetOfTiltSeries',
                      important=True,
                      label='Tilt-series',
                      help='Used to get the tilt angles.')

        form.addParam(TOMO_MASKS, PointerParam,
                      pointerClass=SetOfTomoMasks,
                      label='Tomogram masks (segmentations, opt.)',
                      allowsNull=True,
                      help="Here you can provide a set of masks for matching with dimensions (in pixels) "
                           "equal to the tomogram."
                      )

    # --------------------------- INSERT steps functions ----------------------
    def _insertAllSteps(self):
        self._initialize()
        pidList = []
        for tsId in self.tomoDict.keys():
            cInputId = self._insertFunctionStep(self.convertInputStep, tsId,
                                                prerequisites=[],
                                                needsGPU=False)
            pidList.append(cInputId)

        runId = self._insertFunctionStep(self.runPrepareDataStep,
                                         prerequisites=pidList,
                                         needsGPU=False)
        self._insertFunctionStep(self.validateExecutionStep,
                                 prerequisites=runId,
                                 needsGPU=False)

    # -------------------------- STEPS functions ------------------------------
    def _initialize(self):
        self.makeDirs()
        tsSet = self._getFormAttrib(IN_TS_SET)
        tomoSet = self._getFormAttrib(IN_TOMOS)
        ctfSet = self._getFormAttrib(IN_CTF_SET)
        tomoMasks = self._getFormAttrib(TOMO_MASKS)
        self.samplingRate = tomoSet.getSamplingRate()

        if tomoMasks:
            presentTsIds = getTsIdsIntersection(tsSet, tomoSet, ctfSet, tomoMasks)
            self.tsDict, self.tomoDict, self.ctfDict, self.tomoMaskDict = (
                getTsIdsDicts(tsSet, tomoSet, ctfSet, tomoMasks, present_ts_ids=presentTsIds))
        else:
            presentTsIds = getTsIdsIntersection(tsSet, tomoSet, ctfSet)

            self.tsDict, self.tomoDict, self.ctfDict = (
                getTsIdsDicts(tsSet, tomoSet, ctfSet, present_ts_ids=presentTsIds))

    def convertInputStep(self, tsId: str):
        logger.info(cyanStr(f'tsId = {tsId}: converting the inputs...'))
        try:
            tomo = self.tomoDict[tsId]
            # TomoMask
            if self.tomoMaskDict:
                tomomask = self.tomoMaskDict[tsId]
                msg = check_sr_and_size(tomo, tomomask)
                if msg:
                    self.failedTsIds.append(tsId)
                    logger.info(yellowStr(f'tsId = {tsId} -> {msg}'))
                    return

                inTomoMaskFile = tomomask.getFileName()
                outTomoMaskFile = self._getConvertedOrLinkedNameMask(tsId)
                convertOrLink(inTomoMaskFile, outTomoMaskFile, samplingRate=self.samplingRate)

            # Odd / Even tomograms
            evenFName, oddFNme = sorted(tomo.getHalfMaps(asList=True))
            outTomoFileEven = self._getConvertedOrLinkedNameEven(tsId)  # Tomos are
            convertOrLink(evenFName, outTomoFileEven, samplingRate=self.samplingRate)
            outTomoFileOdd = self._getConvertedOrLinkedNameOdd(tsId)  # Tomos are
            convertOrLink(oddFNme, outTomoFileOdd, samplingRate=self.samplingRate)

            # TODO: check the impact of the parameters angle min and max, and if it is worthy to
            # deal with excluded views up to this point or not

        except Exception as e:
            self.failedTsIds.append(tsId)
            logger.error(redStr(f'tsId = {tsId} -> input conversion failed with the exception -> {e}'))
            logger.error(traceback.format_exc())

    def runPrepareDataStep(self):
        logger.info(cyanStr(f"Preparing the data...'"))

        try:
            tsSet = self._getFormAttrib(IN_TS_SET)
            acq = tsSet.getAcquisition()
            args = self._genPrepareStarCmd(acq)
            Plugin.runIsonet2(self, args)
        except Exception as e:
            logger.error(redStr(f'Data preparation failed with the exception -> {e}'))
            logger.error(traceback.format_exc())

    def validateExecutionStep(self):
        tomoStarFile = self._getTomosStarName()
        if not exists(tomoStarFile):
            raise Exception(f'Tomo star file {tomoStarFile} was not generated.')
        self.setTomoSStarFile(tomoStarFile)
        self._store(tomoStarFile)

    # -------------------------- UTILS functions ------------------------------
    def _genPrepareStarCmd(self, acq: TomoAcquisition) -> str:
        cmd = [
            'prepare_star',
            f'--even {self._getEvenDir()}',
            f'--odd {self._getOddDir()}',
            f'--star_name {self._getTomosStarName()}',
            f'--pixel_size {self.samplingRate}',
            f'--defocus {self._genZeroTiltDefocusList()}',
            f'--cs {acq.getSphericalAberration()}',
            f'--voltage {acq.getVoltage()}',
            f'--ac {acq.getAmplitudeContrast()}',
            f'--tilt_min {acq.getAngleMin()}',
            f'--tilt_max {acq.getAngleMax()}',
            '--create_average True',
        ]
        if self.tomoMaskDict:
            cmd += [f'--mask_folder {self._getMasksDir()}']
        return ' '.join(cmd)

    def _genZeroTiltDefocusList(self) -> List[float]:
        defocusList = []
        for ts, tsId in self.tsDict.items():
            ctf = self.ctfDict[tsId]
            defocusVal = self._getZeroTiltDefocus(ts, ctf)
            defocusList.append(defocusVal)

        return defocusList

    @staticmethod
    def _getZeroTiltDefocus(ts: TiltSeries, ctf: CTFTomoSeries) -> Optional[float]:
        tiList = [ti.clone() for ti in ts.iterItems()]
        ctfList = [ctfTomo.clone() for ctfTomo in ctf.iterItems()]

        # Find the tilt-image with the tilt angle closest to 0.
        tiZeroTilt = min(tiList, key=lambda ti: abs(ti.getTiltAngle()))
        tiZeroTiltAcqOrder = tiZeroTilt.getAcquisitionOrder()

        # Find the corresponding CTF. next() will stop evaluating
        # as soon as it finds the first match
        matchingCtf = None
        for ctfTomo in ctfList:
            if ctfTomo.getAcquisitionOrder() == tiZeroTiltAcqOrder:
                matchingCtf = ctfTomo
                break

        # Return the defocus if a match was found.
        if matchingCtf:
            meanDefocus = (matchingCtf.getDefocusU() + matchingCtf.getDefocusV()) / 2
            return meanDefocus
        else:
            return None

    def makeDirs(self) -> None:
        dirList = [
            self._getOddDir(),
            self._getEvenDir(),
        ]
        if self.tomoMaskDict:
            dirList.append(self._getMasksDir())
        makePath(*dirList)

    def _getConvertedOrLinkedNameOdd(self, tsId: str) -> str:
        return join(self._getOddDir(), f'{tsId}{ODD_SUFFIX}{MRC_EXT}')

    def _getConvertedOrLinkedNameEven(self, tsId: str) -> str:
        return join(self._getEvenDir(), f'{tsId}{EVEN_SUFFIX}{MRC_EXT}')

    def _getConvertedOrLinkedNameMask(self, tsId: str) -> str:
        return join(self._getMasksDir(), f'{tsId}{MASK_SUFFIX}{MRC_EXT}')

    def getTomoStarFile(self) -> str:
        return self._tomoFile.get()

    def setTomoSStarFile(self, val: str) -> None:
        self._tomoFile.set(val)

    def _getOddDir(self) -> str:
        return self._getTmpPath(ODD_DIR)

    def _getEvenDir(self) -> str:
        return self._getTmpPath(EVEN_DIR)

    def _getMasksDir(self) -> str:
        return self._getTmpPath(MASKS_DIR)

    def _getTomosStarName(self) -> str:
        return self._getExtraPath(TOMOGRAMS_STAR)

    # -------------------------- INFO functions ------------------------------
    def _validate(self) -> List[str]:
        errors = []
        inTomos = self._getFormAttrib(IN_TOMOS)
        if not inTomos.hasOddEven():
            errors.append('The even/odd tomograms cannot be found '
                          'in the metadata of the introduced tomograms.')
        return errors
