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
import os
from typing import Tuple, Union, List, Optional

from cistem.protocols import CistemProtTsCtffind
from imod.constants import OUTPUT_TILTSERIES_NAME
from imod.protocols import ProtImodExcludeViews
from isonet2.objects import Isonet2Model
from isonet2.protocols import ProtIsonet2PrepareData, ProtIsonet2Training, ProtIsonet2Predict, ProtIsonet2MakeMask, \
    ProtIsonet2Refine

from pwem.objects import VolumeMask
from pwem.protocols import ProtImportMask
from pyworkflow.tests import setupTestProject, DataSet
from pyworkflow.utils import cyanStr, magentaStr
from tomo.objects import SetOfTiltSeries, SetOfCTFTomoSeries, TiltSeries, CTFTomoSeries, SetOfTomograms, SetOfTomoMasks
from tomo.protocols import ProtImportTs, ProtImportTsCTF, ProtImportTomograms, ProtImportTomomasks
from tomo.protocols.protocol_import_ctf import ImportChoice
from tomo.protocols.protocol_import_tomograms import OUTPUT_NAME
from tomo.tests import DataSetRe4STATuto, RE4_STA_TUTO, EMPIAR_10491_ODD_EVEN, tiltStep, DataSetEmd10491_Odd_Even
from tomo.tests.test_base_centralized_layer import TestBaseCentralizedLayer

TS_1 = 'TS_1'
TS_32 = 'TS_32'

class TestIsonet2(TestBaseCentralizedLayer):
    nTomos = 2
    expectedTomoDims = [1024, 1440, 300]
    excludedViewsDict = {
        TS_1: [0, 1, 2, 40, 41],
        TS_32: [0, 1, 38, 39, 40]
    }
    ctfExcludedViewsDict = {
        TS_1: [0, 1, 38, 39],
        TS_32: [0, 39, 40]
    }
    UNMODIFIED = 'unmodified'
    EXC_VIEWS = 'exc. views'
    RE_STACKED = 're-stacked'

    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.ds = DataSet.getDataSet(EMPIAR_10491_ODD_EVEN)
        cls.sRate = 3.16

    @classmethod
    def _runPreviousProtocols(cls, eVCtf: bool = False, eVTs: bool = False, tomoMasks:bool=False) \
            -> Tuple[SetOfTiltSeries, SetOfCTFTomoSeries]:
        print(cyanStr('--------------------------------- RUNNING PREVIOUS PROTOCOLS ---------------------------------'))
        importedTs = cls._runImportTs()
        if eVTs:
            cls._excludeSetViews(importedTs)
        importedCtfs = cls._runImportCtf(importedTs)
        if eVCtf:
            cls._excludeSetViews(importedCtfs, excludedViewsDict=cls.ctfExcludedViewsDict)
        cls.tomosOddEven = cls._runImportTomograms()
        cls.setOfInputTomoMasks = None
        # if tomoMasks:
        #     cls.setOfInputTomoMasks = cls._runImportTomoMasks(cls.tomosOddEven)
        print(
            cyanStr('\n-------------------------------- PREVIOUS PROTOCOLS FINISHED ---------------------------------'))
        return importedTs, importedCtfs

    @classmethod
    def _excludeSetViews(cls,
                         inSet: Union[SetOfTiltSeries, SetOfCTFTomoSeries],
                         excludedViewsDict: Union[dict, None] = None) -> None:
        if not excludedViewsDict:
            excludedViewsDict = cls.excludedViewsDict
        objList = [obj.clone(ignoreAttrs=[]) for obj in inSet]
        for obj in objList:
            cls._excIntermediateSetViews(inSet, obj, excludedViewsDict[obj.getTsId()])

    @staticmethod
    def _excIntermediateSetViews(inSet: Union[SetOfTiltSeries, SetOfCTFTomoSeries],
                                 obj: Union[TiltSeries, CTFTomoSeries],
                                 excludedViewsList: List[int]) -> None:
        tiList = [ti.clone() for ti in obj]
        for i, ti in enumerate(tiList):
            if i in excludedViewsList:
                ti._objEnabled = False
                obj.update(ti)
        obj.write()
        inSet.update(obj)
        inSet.write()
        inSet.close()

    @classmethod
    def _runImportTs(cls) -> SetOfTiltSeries:
        print(magentaStr("\n==> Importing the tilt series:"))
        acq = DataSetEmd10491_Odd_Even.acq.value
        protImportTs = cls.newProtocol(ProtImportTs,
                                       filesPath=cls.ds.getFile(DataSetEmd10491_Odd_Even.tsDir.value),
                                       filesPattern=DataSetEmd10491_Odd_Even.tsPattern.value,
                                       exclusionWords = '_even.mrcs _odd.mrcs',
                                       anglesFrom=0,  # From range
                                       minAngle=-34,
                                       maxAngle=46,
                                       stepAngle=acq.getStep(),
                                       voltage=acq.getVoltage(),
                                       magnification=acq.getMagnification(),
                                       sphericalAberration=acq.getSphericalAberration(),
                                       amplitudeContrast=acq.getAmplitudeContrast(),
                                       samplingRate=cls.sRate,
                                       doseInitial=acq.getDoseInitial(),
                                       dosePerFrame=acq.getDosePerFrame(),
                                       tiltAxisAngle=acq.getTiltAxisAngle())

        cls.launchProtocol(protImportTs)
        tsImported = getattr(protImportTs, 'outputTiltSeries', None)
        return tsImported

    @classmethod
    def _runImportCtf(cls, importedTs: SetOfTiltSeries) -> SetOfCTFTomoSeries:
        print(magentaStr("\n==> Importing the CTFs:"))
        protImportCtf = cls.newProtocol(ProtImportTsCTF,
                                        filesPath=cls.ds.getFile(DataSetEmd10491_Odd_Even.ctfDir.value),
                                        filesPattern=DataSetEmd10491_Odd_Even.ctfFilesPattern.value,
                                        importFrom=ImportChoice.IMOD.value,
                                        inputSetOfTiltSeries=importedTs)
        cls.launchProtocol(protImportCtf)
        outputCtfs = getattr(protImportCtf, protImportCtf._possibleOutputs.CTFs.name, None)
        return outputCtfs

    @classmethod
    def _runImportTomograms(cls) -> SetOfTomograms:
        print(magentaStr("\n==> Importing the tomograms:"))
        protImportTomos = cls.newProtocol(ProtImportTomograms,
                                          filesPath=cls.ds.getFile(DataSetEmd10491_Odd_Even.tomoDir.value),
                                          filesPattern=DataSetEmd10491_Odd_Even.pattern.value,
                                          samplingRate=cls.sRate,
                                          importOddEven=True)
        cls.launchProtocol(protImportTomos)
        tomoOddEven = getattr(protImportTomos, OUTPUT_NAME, None)
        return tomoOddEven

    # @classmethod
    # def _runImportTomoMasks(cls,importedTomo: SetOfTomograms)->SetOfTomoMasks:
    #     print(magentaStr(f"\n==> Importing a set of tomoMasks:"))
    #     protImportTomomasks = cls.newProtocol(ProtImportTomomasks,
    #                                           filesPath=filesPath,
    #                                           filesPattern=filesPattern,
    #                                           samplingRate=cls.sRate,
    #                                           inputTomos=importedTomo)
    #     cls.launchProtocol(protImportTomomasks)
    #     return getattr(protImportSetOfTomoMasks, ProtImportTomomasks._possibleOutputs.tomomasks.name, None)

    @classmethod
    def _runExcludeViewsProt(cls,
                             inTsSet: SetOfTiltSeries,
                             objLabel: str = None) -> SetOfTiltSeries:
        print(magentaStr("\n==> Running the TS exclusion of views:"))
        protExcViews = cls.newProtocol(ProtImodExcludeViews, inputSetOfTiltSeries=inTsSet)
        if objLabel:
            protExcViews.setObjLabel(objLabel)
        cls.launchProtocol(protExcViews)
        outTsSet = getattr(protExcViews, OUTPUT_TILTSERIES_NAME, None)
        return outTsSet

    @classmethod
    def _runCistemEstimateCtf(cls, inTsSet: SetOfTiltSeries) -> SetOfCTFTomoSeries:
        print(magentaStr("\n==> Estimating the CTF with Cistem:"))
        protEstimateCtf = cls.newProtocol(CistemProtTsCtffind,
                                          inputTiltSeries=inTsSet,
                                          lowRes=50,
                                          highRes=5,
                                          minDefocus=5000,
                                          maxDefocus=50000)
        cls.launchProtocol(protEstimateCtf)
        return getattr(protEstimateCtf, CistemProtTsCtffind._possibleOutputs.CTFs.name, None)

    @classmethod
    def _genReStackedCtf(cls) -> SetOfCTFTomoSeries:
        tsSet = cls._runImportTs()
        # Exclude some views from the TS at metadata level
        cls._excludeSetViews(tsSet, excludedViewsDict=cls.ctfExcludedViewsDict)
        # Re-stack that TS
        reStackedTsSet = cls._runExcludeViewsProt(tsSet)
        # Estimate the CTF using the re-stacked TS
        return cls._runCistemEstimateCtf(reStackedTsSet)

    def _runIsonet2PrepareData(self,
                               inCtfSet: SetOfCTFTomoSeries,
                               inTsSet: SetOfTiltSeries,
                               ctfSetMsg: str,
                               tsSetMsg: str) -> ProtIsonet2PrepareData:
        print(magentaStr(f"\n==> Running the Prepare Data:"
                         f"\n\t- CTFs: {ctfSetMsg}"
                         f"\n\t- Tilt-series = {tsSetMsg}"))
        protPrepareData = self.newProtocol(ProtIsonet2PrepareData,
                                           inTomos=self.tomosOddEven,
                                           inCtfSet=inCtfSet,
                                           inTsSet=inTsSet,
                                           tomoMasks=self.setOfInputTomoMasks
                                           )
        objLabel = f'Isonet2 - Prepare Data: ts {tsSetMsg}, ctf {ctfSetMsg}'
        protPrepareData.setObjLabel(objLabel)
        self.launchProtocol(protPrepareData)
        return protPrepareData

    def _checkStar(self, protPrepareData: ProtIsonet2PrepareData) -> None:
        starFile=protPrepareData.getTomoStarFile()
        self.assertTrue(os.path.exists(starFile), f'{starFile} was not generated')  # check if the star file exists

    def _runIsonet2Training(self, inProt: ProtIsonet2PrepareData) \
            -> Optional[Isonet2Model]:
        print(magentaStr(f"\n==> Prepare Data ==> Training step"))
        protTraining = self.newProtocol(ProtIsonet2Training,
                                        prepDataProt=inProt,
                                        epochs=1,
                                        save_interval=1
                                        )
        self.launchProtocol(protTraining)
        modelName = f'{protTraining._possibleOutputs.model.name}_full' #use the final model
        modelTraining = getattr(protTraining, modelName, None)
        return modelTraining

    def _checkModel(self, model:Isonet2Model) -> None:
        # Check the Model
        self.assertIsNotNone(model, 'The training did not produce the final model') #check if the output exists
        modelPath=model.getPath()
        self.assertTrue(os.path.exists(modelPath),f'{modelPath} does not exist') #check if the file exists

    def _runIsonet2Predict(self, inProt: Union[ProtIsonet2PrepareData, ProtIsonet2Refine], model: Isonet2Model) \
            -> Tuple[ProtIsonet2Predict, Optional[SetOfTomograms]]:
        print(magentaStr(f"\n==> Prepare Data ==> Training step ==> Predict step"))
        protPredict = self.newProtocol(ProtIsonet2Predict,
                                       inProt=inProt,
                                       model=model
                                       )
        self.launchProtocol(protPredict)
        setofTomos = getattr(protPredict, protPredict._possibleOutputs.tomograms.name, None)
        return protPredict, setofTomos

    def _checkSetOfTomos(self, setOfTomos: SetOfTomograms, expectedSize:int=2) -> None:
        # Check the Tomograms
        acq = DataSetEmd10491_Odd_Even.acq.value
        self.checkTomograms(inTomoSet=setOfTomos,
                            expectedSetSize=expectedSize,
                            expectedSRate=self.sRate,
                            expectedDimensions=self.expectedTomoDims,
                            hasOddEven=True,
                            hasHalves=True,
                            testSetAcqObj=acq,
                            testAcqObj=acq)

    def _runIsonet2MakeMask(self, inProt: ProtIsonet2Predict) \
            -> Tuple[ProtIsonet2MakeMask, Optional[SetOfTomoMasks]]:
        print(magentaStr(f"\n==> Prepare Data ==> Training step ==> Predict step ==> Make mask step"))
        protMakeMask = self.newProtocol(ProtIsonet2MakeMask,
                                        inProt=inProt)
        self.launchProtocol(protMakeMask)
        setofTomoMasks = getattr(protMakeMask, protMakeMask._possibleOutputs.masks.name, None)
        return protMakeMask, setofTomoMasks

    def _checkSetOfMasks(self, setofTomoMasks: SetOfTomoMasks,expectedSize:int=2) -> None:
        # Check the set of tomoMask generated by ProtIsonet2MakeMask
        self.checkTomoMasks(inTomoMasks=setofTomoMasks,
                            expectedSetSize=expectedSize,
                            expectedSRate=self.sRate,
                            expectedDimensions=self.expectedTomoDims)

    def _runIsonet2Refine(self, inProt: ProtIsonet2MakeMask) \
            -> Tuple[ProtIsonet2Refine, Optional[Isonet2Model]]:
        print(magentaStr(f"\n==> Prepare Data ==> Training step ==> Predict step ==> Make mask step ==> Refine step"))
        protRefine = self.newProtocol(ProtIsonet2Refine,
                                      inProt=inProt,
                                      epochs=1,
                                      save_interval=1
                                      )
        self.launchProtocol(protRefine)
        modelName = f'{protRefine._possibleOutputs.model.name}_full'
        modelRefine = getattr(protRefine, modelName, None)
        return protRefine, modelRefine

    # TEST
    def _runTestIsonet2(self,
                        inCtfSet: SetOfCTFTomoSeries,
                        inTsSet: SetOfTiltSeries,
                        ctfSetMsg: str,
                        tsSetMsg: str) -> None:
        # Run Prepare Data
        protPrepareData = self._runIsonet2PrepareData(inCtfSet=inCtfSet,
                                                      inTsSet=inTsSet,
                                                      ctfSetMsg=ctfSetMsg,
                                                      tsSetMsg=tsSetMsg)
        # Check if the star file was generated
        self._checkStar(protPrepareData)
        # Run Training (Denoise)
        modelTraining = self._runIsonet2Training(protPrepareData)
        # Check the training model
        self._checkModel(modelTraining)
        # Run Predict
        protPredict, setofTomos = self._runIsonet2Predict(protPrepareData, modelTraining)
        # Check the tomograms
        self._checkSetOfTomos(setofTomos)
        # Run MakeMask
        protMakeMask, setofTomoMasks = self._runIsonet2MakeMask(protPredict)
        # Check the masks
        self._checkSetOfMasks(setofTomoMasks)
        #Run Refine
        protRefine, modelRefine = self._runIsonet2Refine(protMakeMask)
        # Check the refine model
        self._checkModel(modelRefine)
        #Run Predict
        protPredict, setofTomos = self._runIsonet2Predict(protRefine, modelRefine)
        # Check the tomograms
        self._checkSetOfTomos(setofTomos)

    def testIsonet2(self):
        importedTs, importedCtfs = self._runPreviousProtocols()
        self._runTestIsonet2(inCtfSet=importedCtfs,
                             inTsSet=importedTs,
                             ctfSetMsg=self.UNMODIFIED,
                             tsSetMsg=self.UNMODIFIED)

    def testIsonet2_EV_Ctf(self):
        importedTs, importedCtfs = self._runPreviousProtocols(eVCtf=True)
        self._runTestIsonet2(inCtfSet=importedCtfs,
                             inTsSet=importedTs,
                             ctfSetMsg=self.EXC_VIEWS,
                             tsSetMsg=self.UNMODIFIED)

    def testIsonet2_EV_Ts(self):
        importedTs, importedCtfs = self._runPreviousProtocols(eVTs=True)
        self._runTestIsonet2(inCtfSet=importedCtfs,
                             inTsSet=importedTs,
                             ctfSetMsg=self.UNMODIFIED,
                             tsSetMsg=self.EXC_VIEWS)

    def testIsonet2_EV_Restacked_Ctf(self):
        importedTs, _ = self._runPreviousProtocols()
        ctfSetReStacked = self._genReStackedCtf()  # Gen a CTF estimated on a re-stacked TS
        self._runTestIsonet2(inCtfSet=ctfSetReStacked,
                             inTsSet=importedTs,
                             ctfSetMsg=self.EXC_VIEWS,
                             tsSetMsg=self.UNMODIFIED)

    def testIsonet2_EV_Restacked_Ts(self):
        importedTs, importedCtfs = self._runPreviousProtocols(eVTs=True)
        tsSetReStacked = self._runExcludeViewsProt(importedTs)  # Re-stack the TS
        self._runTestIsonet2(inCtfSet=importedCtfs,
                             inTsSet=tsSetReStacked,
                             ctfSetMsg=self.UNMODIFIED,
                             tsSetMsg=self.EXC_VIEWS)

    # def testIsonet2_TomoMasks(self):
    #     importedTs, importedCtfs = self._runPreviousProtocols(tomoMasks=True)
    #     self._runTestIsonet2(inCtfSet=importedCtfs,
    #                          inTsSet=importedTs,
    #                          ctfSetMsg=self.UNMODIFIED,
    #                          tsSetMsg=self.UNMODIFIED)








