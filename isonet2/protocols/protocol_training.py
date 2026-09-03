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
from os.path import join, exists
from typing import List

from isonet2 import Plugin
from isonet2.constants import PREPARE_DATA_PROT, CTF_NONE, UNET_MEDIUM, L2, TOMOGRAMS_STAR, ARCH_CHOICES, \
    LOSS_FUNC_CHOICES, CTF_MODE_CHOICES, CFP_MODE_CONSTANT_CLIP
from isonet2.objects import Isonet2Model
from isonet2.protocols.protocol_base import ProtIsonet2Base
from pyworkflow import BETA
from pyworkflow.protocol import PointerParam, GPU_LIST, StringParam, EnumParam, BooleanParam, FloatParam, \
    LEVEL_ADVANCED, IntParam, GT, GE
from pyworkflow.utils import Message, cyanStr, redStr, makePath

logger = logging.getLogger(__name__)


class Outputobjects(Enum):
    model = Isonet2Model


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
                      label='Isonet2 Prepare data protocol')

        form.addParam('pretrained_choice', BooleanParam,
                      label='Load pretrained model',
                      default=False,
                      help='Pretrained model to continue training. Previous method, architecture, cube_size, '
                           'ctf_mode, and metrics will be loaded.'
                      )
        form.addParam('pretrained_model', PointerParam,
                      pointerClass='Isonet2Model',
                      label='Isonet pretrained model',
                      condition='pretrained_choice',
                      )

        form.addSection(label='CTF Mode')
        form.addParam('ctf_mode', EnumParam,
                      label='CTF mode',
                      choices=['None', 'phase_only', 'wiener', 'network'],
                      default=CTF_NONE,
                      display=EnumParam.DISPLAY_HLIST,
                      allowsNull=False,
                      help='CTF handling mode: "None", "phase_only", "wiener", or "network". '
                           '"None": No CTF correction. '
                           '"phase_only": Phase-only correction. '
                           '"wiener": Applies CTF-shaped filter to network input. '
                           '"network": Applier Wiener filter to network target.'

                      )
        form.addParam('isCTFflipped', BooleanParam,
                      label='Is CTF flipped?',
                      default=False,
                      condition='ctf_mode != 0',
                      help='Whether input tomograms are phase flipped.'
                      )
        form.addParam('do_phaseflip_input', BooleanParam,
                      label='Phase flip the input',
                      default=True,
                      condition='ctf_mode != 0',
                      help='Whether to apply phase flip during training.'
                      )
        form.addParam('clip_first_peak_mode', EnumParam,
                      label='Clip first peak mode',
                      choices=['none', 'constant clip', 'negative sine', 'cosine'],
                      default=CFP_MODE_CONSTANT_CLIP,
                      display=EnumParam.DISPLAY_HLIST,
                      condition='ctf_mode != 0',
                      help='Controls attenuation of overrepresented very-low-frequency CTF peak.'
                           'Options "negative sine" and "cosine" might increase low-resolution contrast.'
                      )
        form.addParam('b_factor', FloatParam,
                      label='B-factor',
                      default=0,
                      help='B-factor applied during training/prediction to boost high-frequency content. '
                           'For cellular tomograms we recommend a b-factor of 0. For isolated samples, '
                           'you can use a b-factor from 200–300. '
                      )
        group = form.addGroup('CTF Deconvolution',
                              condition='ctf_mode != 0',
                              expertLevel=LEVEL_ADVANCED
                              )
        group.addParam('ctf_deconvolution', BooleanParam,
                       label='Apply CTF Deconvolution',
                       default=False
                       )
        group.addParam('snr_falloff', FloatParam,
                       label='SNR falloff',
                       default=0,
                       condition='ctf_deconvolution',
                       help='Controls frequency-dependent SNR attenuation applied during deconvolution; '
                            'larger values reduce high-frequency contribution more aggressively.'
                       )
        group.addParam('deconv_strength', FloatParam,
                       label='Deconvolution strength',
                       default=1.0,
                       condition='ctf_deconvolution',
                       help='Scalar multiplier for deconvolution strength; increasing this emphasizes correction '
                            'and low-frequency recovery.'
                       )
        group.addParam('highpass_nyquist', FloatParam,
                       label='Highpass Nyquist',
                       default=0.02,
                       condition='ctf_deconvolution',
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
                      expertLevel=LEVEL_ADVANCED,
                      help='Loss function to use for training: L1, Huber, L2.'
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
                       help='Run prediction every saved interval.'
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
        self._insertFunctionStep(self.trainingStep, needsGPU=True)
        self._insertFunctionStep(self.createOutputStep, needsGPU=False)

    # -------------------------- STEPS functions ------------------------------
    def _initialize(self):
        makePath(self._getModelOutDir())

    def trainingStep(self):
        logger.info(cyanStr(f' Training step...'))

        try:
            args = self._generateArguments()
            Plugin.runIsonet2(self, args, useGpu=True)
        except Exception as e:
            logger.error(redStr(f'Denoise training failed with the exception -> {e}'))
            logger.error(traceback.format_exc())

    def createOutputStep(self):
        modelFile = self._getModelPath()
        if not exists(modelFile):
            raise Exception(f'Model file {modelFile} was not generated.')

        model = Isonet2Model(model_file=modelFile)  # wrap in isonet2model scipion object
        self._defineOutputs(**{Outputobjects.model.name: model})

        # output e relazioni

    # -------------------------- UTILS functions ------------------------------
    def _getModelOutDir(self):
        return self._getExtraPath('training')

    def _getModelPath(self):
        arch = ARCH_CHOICES[self.arch.get()]
        return join(self._getModelOutDir(), f'network_n2n_{arch}_{self.cube_size.get()}_full.pt')

    def _getPretrainedModelPath(self, pretrained_model: Isonet2Model):
        return pretrained_model.getPath()

    def _generateArguments(self) -> str:
        output_dir = self._getModelOutDir()
        starFile = self._getStarFile()
        gpu = ' '.join([str(el) for el in self.getGpuList()])
        pretrained_model = self.pretrained_model.get()
        ctf_mode = self.ctf_mode.get()
        arch = self.arch.get()
        loss = self.loss_func.get()

        cmd = [
            'denoise',
            f'--star_file {starFile}',
            f'--output_dir {output_dir}',
            f'--gpuID {gpu}',
            f'--ncpus {self.ncpus.get()}',
            f'--cube_size {self.cube_size.get()}',
            f'--epochs {self.epochs.get()}',
            f'--batch_size {self.batch_size.get()}',
            f'--save_interval {self.save_interval.get()}',
            f'--learning_rate {self.learning_rate.get()}',
            f'--learning_rate_min {self.learning_rate_min.get()}',
            f'--mixed_precision {self.mixed_precision.get()}',
            f'--CTF_mode {CTF_MODE_CHOICES[self.ctf_mode.get()]}',
            f'--bfactor {self.b_factor.get()}',
            f'--with_preview {self.with_preview.get()}'

        ]

        if arch != UNET_MEDIUM:
            cmd.append(f'--arch {ARCH_CHOICES[self.arch.get()]}')

        if loss != L2:
            cmd.append(f'--loss_func {LOSS_FUNC_CHOICES[self.loss_func.get()]}')

        if not ctf_mode == CTF_NONE:
            cmd.append(f'--isCTFflipped {self.isCTFflipped.get()}')
            cmd.append(f'--do_phaseflip_input {self.do_phaseflip_input.get()}')
            cmd.append(f'--clip_first_peak_mode {self.clip_first_peak_mode.get()}')

            if self.ctf_deconvolution.get():
                cmd.append(f'--snrfalloff {self.snr_falloff.get()}')
                cmd.append(f'--deconvstrength {self.deconv_strength.get()}')
                cmd.append(f'--highpassnyquist {self.highpass_nyquist.get()}')

        if self.pretrained_choice:
            pretrainedPath = self._getPretrainedModelPath(pretrained_model)
            cmd.append(f'--pretrained_model {pretrainedPath}')

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
