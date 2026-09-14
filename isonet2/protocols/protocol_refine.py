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
from enum import Enum

from isonet2.constants import PREPARE_DATA_PROT, CTF_NONE, CFP_MODE_CONSTANT_CLIP, UNET_MEDIUM, MAKE_MASK_PROT
from isonet2.objects import Isonet2Model
from isonet2.protocols.protocol_base import ProtIsonet2Base
from pyworkflow import BETA
from pyworkflow.protocol import PointerParam, BooleanParam, EnumParam, FloatParam, LEVEL_ADVANCED, GE, GT, StringParam, \
    IntParam, GPU_LIST
from pyworkflow.utils import Message

logger = logging.getLogger(__name__)


class Outputobjects(Enum):
    model = Isonet2Model

class ProtIsonet2Refine(ProtIsonet2Base):
    """Use refine for IsoNet2 missing-wedge correction (isonet2) or isonet2-n2n combined modes."""

    _label = 'Isonet2 refine'
    _devStatus = BETA

    # _possibleOutputs = Outputobjects

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    # --------------------------- DEFINE param functions ----------------------
    def _defineParams(self, form):
        form.addSection(label=Message.LABEL_INPUT)
        form.addParam(MAKE_MASK_PROT, PointerParam,
                      pointerClass='ProtIsonet2MakeMask',
                      important=True,
                      label='Isonet2 Make Mask protocol')

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
                           '"wiener":Applier Wiener filter to network target.'
                           '"network": Applies CTF-shaped filter to network input. '
                      )
        form.addParam('isCTFflipped', BooleanParam,
                      label='Is the tomogram CTF flipped?',
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
                       validators=[GE(0)],
                       condition='ctf_deconvolution',
                       help='Controls frequency-dependent SNR attenuation applied during deconvolution; '
                            'larger values reduce high-frequency contribution more aggressively.'
                       )
        group.addParam('deconv_strength', FloatParam,
                       label='Deconvolution strength',
                       default=1.0,
                       validators=[GT(0)],
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
                      expertLevel=LEVEL_ADVANCED,
                      validators=[GT(0)],
                      help='Initial learning rate.'
                      )
        form.addParam('learning_rate_min', FloatParam,
                      label='Minimum learning rate',
                      default=3e-4,
                      expertLevel=LEVEL_ADVANCED,
                      validators=[GT(0)],
                      help='Minimum learning rate for scheduler.'
                      )
        form.addParam('loss_func', EnumParam,
                      label='Loss function',
                      choices=['L1', 'HUBER', 'L2'],
                      default=L2,
                      expertLevel=LEVEL_ADVANCED,
                      help='Loss function to use for training: L1, Huber, L2.'
                      )
        form.addParam('mixed_precision', BooleanParam,
                      label='Use mixed precision?',
                      default=True,
                      expertLevel=LEVEL_ADVANCED,
                      help='If set to "Yes", float16/mixed precision to reduce VRAM and speed up training is used.'
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
                       default=False,
                       help='Run prediction every saved interval.'
                       )
        group.addParam('prev_tomo_idx', StringParam,
                       label='Preview tomogram index(es)',
                       condition='with_preview',
                       default=1,
                       help='If set, automatically predict only the tomograms listed by these indices '
                            '(e.g., "1,2,4" or "5-10,15,16")'
                       )

        form.addHidden(GPU_LIST, StringParam,
                       default='0',
                       label="Choose GPU IDs",
                       help=""
                       )
        form.addParallelSection(threads=8, mpi=0)


