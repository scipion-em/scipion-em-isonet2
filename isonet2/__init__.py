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

import pwem
from isonet2.constants import ISONET2_CUDA_LIB, ISONET2_DEFAULT_ACTIVATION_CMD, ISONET2_ENV_ACTIVATION, ISONET2_HOME, \
    ISONET2, ISONET2_DEFAULT_HASH
from pyworkflow import TOMO


__version__ = '3.0.0'

from pyworkflow.utils import Environ

_logo = "icon.png"
_references = ['Liu2022']


class Plugin(pwem.Plugin):
    _pathVars = [ISONET2_CUDA_LIB]
    _url = "https://github.com/scipion-em/scipion-em-isonet2"
    _processingField = [TOMO]

    @classmethod
    def _defineVariables(cls):
        cls._defineVar(ISONET2_ENV_ACTIVATION, ISONET2_DEFAULT_ACTIVATION_CMD)
        cls._defineVar(ISONET2_CUDA_LIB, pwem.Config.CUDA_LIB)
        cls._defineEmVar(ISONET2_HOME, ISONET2 + '-' + ISONET2_DEFAULT_HASH)

    @classmethod
    def getIsonet2EnvActivation(cls):
        return cls.getVar(ISONET2_ENV_ACTIVATION)

    @classmethod
    def getEnviron(cls):
        """ Set up the environment variables needed to launch gapstop. """
        environ = Environ(os.environ)
        if 'PYTHONPATH' in environ:
            # this is required for python virtual env to work
            del environ['PYTHONPATH']
        cudaLib = cls.getVar(ISONET2_CUDA_LIB, pwem.Config.CUDA_LIB)
        environ.addLibrary(cudaLib)