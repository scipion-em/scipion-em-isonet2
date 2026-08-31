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

from pyperclip import lazy_load_stub_copy

from isonet2.constants import PREPARE_DATA_PROT, CTF_NONE, CTF_PHASE_ONLY, CTF_WIENER, CTF_NETWORK, \
    PEAK_MODE_CONSTANT_CLIP
from isonet2.protocols.protocol_base import ProtIsonet2Base
from pyworkflow import BETA
from pyworkflow.protocol import PointerParam, GPU_LIST, StringParam, EnumParam, BooleanParam, FloatParam, LEVEL_ADVANCED
from pyworkflow.utils import Message

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

        form.addParam('pretrained_model', PointerParam,
                      pointerClass='ProtIsonet2PretrainedModel',
                      label='Isonet pretrained model',
                      allowsNull=True,
                      help='Pretrained model to continue training. Previous method, arch, cube_size, '
                           'CTF_mode, and metrics will be loaded.'
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
                      help='Whether input tomograms are phase flipped.')
        form.addParam('do_phaseflip_input', BooleanParam,
                      label='Do phase flip input',
                      default=True,
                      condition='CTF_mode != 0',
                      help='Whether to apply phase flip during training.'
                      )
        form.addParam('b_factor', FloatParam,
                      label='B-factor',
                      default=0,
                      help='B-factor applied during training/prediction to boost high-frequency content. For cellular '
                           'tomograms we recommend a b-factor of 0. For isolated samples, you can use a b-factor '
                           'from 200–300. '
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
        form.addParam('snr_falloff', FloatParam,
                      label='SNR falloff',
                      default=0,
                      expertLevel=LEVEL_ADVANCED,
                      help='Controls frequency-dependent SNR attenuation applied during deconvolution; '
                           'larger values reduce high-frequency contribution more aggressively.'
                      )
        form.addParam('deconv_strength',FloatParam,
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
                           'large-scale intensity gradients and drift.')


        # #vedi
        # form.addHidden(GPU_LIST, StringParam,
        #                default='0',
        #                label="Choose GPU IDs",
        #                help=""
        #                )
        #
