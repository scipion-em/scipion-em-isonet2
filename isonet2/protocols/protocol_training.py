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
from typing import List

from isonet2 import Plugin
from isonet2.constants import PREPARE_DATA_PROT, CTF_NONE, UNET_MEDIUM, L2, TOMOGRAMS_STAR, ARCH_CHOICES, \
    LOSS_FUNC_CHOICES, CTF_MODE_CHOICES
from isonet2.objects import Isonet2Model
from isonet2.protocols.protocol_base import ProtIsonet2Base
from pyworkflow import BETA
from pyworkflow.protocol import PointerParam, GPU_LIST, StringParam, EnumParam, BooleanParam, FloatParam, \
    LEVEL_ADVANCED, IntParam, GT
from pyworkflow.utils import Message, cyanStr, redStr, makePath

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

        form.addParam('pretrained_choice',BooleanParam,
                      label='Load pretrained model',
                      default=False,
                      help='Pretrained model to continue training. Previous method, architecture, cube_size, '
                           'CTF_mode, and metrics will be loaded.'
                      )
        form.addParam('pretrained_model', PointerParam,
                      pointerClass='Isonet2Model',
                      label='Isonet pretrained model',
                      condition='pretrained_choice',
                      )

        form.addSection(label='CTF Mode')
        form.addParam('CTF_mode', EnumParam,
                      label='CTF mode',
                      choices=['None', 'phase_only', 'wiener', 'network'],
                      default=CTF_NONE,
                      display=EnumParam.DISPLAY_HLIST,
                      allowsNull=False,
                      help='CTF handling mode: "None", "phase_only", "wiener", or "network".'
                      )
        form.addParam('isCTFflipped', BooleanParam,
                      label='Is CTF flipped?',
                      default=False,
                      condition='CTF_mode != 0',
                      help='Whether input tomograms are phase flipped.'
                      )
        form.addParam('do_phaseflip_input', BooleanParam,
                      label='Phase flip the input',
                      default=True,
                      condition='CTF_mode != 0',
                      help='Whether to apply phase flip during training.'
                      )
        form.addParam('clip_first_peak_mode', EnumParam,
                      label='Clip first peak mode',
                      choices=['none', 'constant clip', 'negative sine', 'cosine'],
                      default=1,
                      display=EnumParam.DISPLAY_HLIST,
                      condition='CTF_mode != 0',
                      help='Controls attenuation of overrepresented very-low-frequency CTF peak.'
                           '0: none, 1: constant clip, 2: negative sine, 3: cosine.'
                           'Options 2 and 3 might increase low-resolution contrast.'
                      )
        form.addParam('b_factor', FloatParam,
                      label='B-factor',
                      default=0,
                      help='B-factor applied during training/prediction to boost high-frequency content. '
                           'For cellular tomograms we recommend a b-factor of 0. For isolated samples, '
                           'you can use a b-factor from 200–300. '
                      )

        form.addParam('snr_falloff', FloatParam,
                      label='SNR falloff',
                      default=0,
                      expertLevel=LEVEL_ADVANCED,
                      help='Controls frequency-dependent SNR attenuation applied during deconvolution; '
                           'larger values reduce high-frequency contribution more aggressively.'
                      )
        form.addParam('deconv_strength', FloatParam,
                      label='Deconvolution strength',
                      default=1.0,
                      expertLevel=LEVEL_ADVANCED,
                      help='Scalar multiplier for deconvolution strength; increasing this emphasizes correction '
                           'and low-frequency recovery.'
                      )
        form.addParam('highpass_nyquist', FloatParam,
                      label='Highpass nyquist',
                      default=0.02,
                      expertLevel=LEVEL_ADVANCED,
                      help='Fraction of the Nyquist used as a very-low-frequency high-pass cutoff; use to remove '
                           'large-scale intensity gradients and drift.'
                      )

        form.addSection(label='Training Parameters')
        form.addParam('arch', EnumParam,
                      label='Architecture',
                      choices=['unet-small', 'unet-medium', 'unet-large'],
                      default=UNET_MEDIUM,
                      display=EnumParam.DISPLAY_HLIST,
                      expertLevel=LEVEL_ADVANCED,
                      help='Network architecture (e.g., unet-small, unet-medium, unet-large). '
                           'Determines model capacity and VRAM requirements.'
                      )
        form.addParam('batch_size', StringParam,
                      label='Batch size',
                      default='auto',
                      help='Number of subtomograms per optimization step; if "auto", this is automatically determined '
                           'by multiplying the number of available GPUs by 2. If the number of GPUs is 1, '
                           'batch size is 4. Batch size per GPU matters for gradient stability.'
                      )
        form.addParam('cube_size', IntParam,
                      label='Cube size',
                      default=96,
                      help='Size in voxels of training subvolumes. '
                           'Must be compatible with the network (divisible by the network downsampling factors).'
                      )
        form.addParam('epochs', IntParam,
                      label='Epochs',
                      default=50,
                      validators=[GT(0)],
                      help='Number of training epochs.'
                      )
        form.addParam('learning_rate', FloatParam,
                      label='Learning rate',
                      default=3e-4,
                      validators=[GT(0)],
                      help='Initial learning rate.'
                      )
        form.addParam('learning_rate_min', FloatParam,
                      label='Minimum learning rate',
                      default=3e-4,
                      expertLevel=LEVEL_ADVANCED,
                      help='Minimum learning rate for scheduler.'
                      )
        form.addParam('loss_func', EnumParam,
                      label='Loss function',
                      choices=['L1', 'HUBER', 'L2'],
                      default=L2,
                      help='Loss function to use for training: L1,Huber,L2.'
                      )

        group = form.addGroup('Checkpoints & preview')
        group.addParam('save_interval', IntParam,
                       label='Save interval (epochs)',
                       default=10,
                       validators=[GT(0)],
                       help='Interval to save model checkpoints.'
                       )
        group.addParam('with_preview', BooleanParam,
                       label='Preview during training?',
                       default=True,
                       help='Run prediction every save interval.'
                       )
        group.addParam('prev_tomo_idx', StringParam,
                       label='Preview tomogram index(es)',
                       condition='with_preview',
                       default=1,
                       help='If set, automatically predict only the tomograms listed by these indices '
                            '(e.g., "1,2,4" or "5-10,15,16")'
                       )

        form.addSection(label='Additional Parameters')
        form.addParam('ncpus', IntParam,
                      label='Number of cpus',
                      default=16,
                      help='Number of CPUs to use for data processing.')
        form.addParam('mixed_precision', BooleanParam,
                      label='Use mixed precision?',
                      default=True,
                      help='If set to "Yes", float16/mixed precision to reduce VRAM and speed up training is used.')

        form.addHidden(GPU_LIST, StringParam,
                       default='0',
                       label="Choose GPU IDs",
                       help=""
                       )

    # --------------------------- INSERT steps functions ----------------------
    def _insertAllSteps(self):

        self._initialize()

        self._insertFunctionStep(self.trainingStep,needsGPU=True)
        self._insertFunctionStep(self.createOutputStep,needsGPU=False)

    # -------------------------- STEPS functions ------------------------------
    def _initialize(self):
        makePath(self._getModelDir())


    def trainingStep(self):
        logger.info(cyanStr(f' Training step...'))

        try:
            args = self._generateArguments()
            Plugin.runIsonet2(self, args, useGpu=True)
        except Exception as e:
            logger.error(redStr(f'Denoise training failed with the exception -> {e}'))
            logger.error(traceback.format_exc())


    def createOutputStep(self):
        pass
        # modelFile = self._getModelPath()
        # if not exists(modelFile):
        #     raise Exception(f'Model file {modelFile} was not generated.')
        #
        # model = Isonet2Model(model_file=modelFile)

        #output e relazioni

    # -------------------------- UTILS functions ------------------------------
    def _getModelDir(self):
        return self._getExtraPath('training')

    def _getModelPath(self):
        arch = ARCH_CHOICES[self.arch.get()]
        return join(self._getModelDir(),f'network_n2n_{arch}_{self.cube_size.get()}_full.pt')

    #getmodelfile x pretrained

    def _generateArguments(self) -> str:
        output_dir=self._getModelDir()
        starFile = self._getStarFile()
        gpu = ' '.join([str(el) for el in self.getGpuList()])
        pretrained_model = self.pretrained_model.get()

        cmd = [
            'denoise',
            f'--star_file {starFile}',
            f'--output_dir {output_dir}',
            f'--gpuID {gpu}',
            f'--ncpus {self.ncpus.get()}',
            f'--arch {ARCH_CHOICES[self.arch.get()]}',
            f'--cube_size {self.cube_size.get()}',
            f'--epochs {self.epochs.get()}',
            f'--batch_size {self.batch_size.get()}',
            f'--loss_func {LOSS_FUNC_CHOICES[self.loss_func.get()]}',
            f'--save_interval {self.save_interval.get()}',
            f'--learning_rate {self.learning_rate.get()}',
            f'--learning_rate_min {self.learning_rate_min.get()}',
            f'--mixed_precision {self.mixed_precision.get()}',
            f'--CTF_mode {CTF_MODE_CHOICES[self.CTF_mode.get()]}',
            f'--isCTFflipped {self.isCTFflipped.get()}',
            f'--do_phaseflip_input {self.do_phaseflip_input.get()}',
            f'--bfactor {self.b_factor.get()}',
            f'--clip_first_peak_mode {self.clip_first_peak_mode.get()}',
            f'--snrfalloff {self.snr_falloff.get()}',
            f'--deconvstrength {self.deconv_strength.get()}',
            f'--highpassnyquist {self.highpass_nyquist.get()}',
            f'--with_preview {self.with_preview.get()}'


        ]

        if pretrained_model:
            pass

        if self.with_preview.get():
            cmd.append(f'--prev_tomo_idx {self.prev_tomo_idx.get()}')

        return ' '.join(cmd)

    # --------------------------- INFO functions ------------------------------

    def _validate(self) -> List[str]:
        valmsg = []
        cube_size = self.cube_size.get()
        lr = self.learning_rate.get()
        lr_min = self.learning_rate_min.get()
        save_interval = self.save_interval.get()
        epochs = self.epochs.get()

        if cube_size < 64 or cube_size % 16 != 0:
            valmsg.append('Cube size must be higher than 64 and a multiple of 16.')

        if lr_min > lr:
            valmsg.append('Minimum learning rate must be lower than the initial learning rate.')

        if save_interval > epochs:
            valmsg.append('Save interval cannot be greater than the total number of epochs.')

        return valmsg
