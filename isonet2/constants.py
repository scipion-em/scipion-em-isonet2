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
ISONET2 = 'IsoNet2'
ISONET2_HOME = 'ISONET2_HOME'
ISONET2_CUDA_LIB = 'ISONET2_CUDA_LIB'
ISONET2_ENV_ACTIVATION = 'ISONET2_ENV_ACTIVATION'

ISONET2_DEFAULT_HASH = '6c5c7bb'
ISONET2_HASH_DATE = '20260519'
ISONET2_DEFAULT_VERSION = f'{ISONET2_DEFAULT_HASH}-{ISONET2_HASH_DATE}'
ISONET2_ENV_NAME = f'{ISONET2}-{ISONET2_DEFAULT_VERSION}'
ISONET2_DEFAULT_ACTIVATION_CMD = f'conda activate {ISONET2_ENV_NAME}'

# Directories
EVEN_DIR = 'even'
ODD_DIR = 'odd'
MASKS_DIR = 'masks'

# Files
TOMOGRAMS_STAR = 'inTomograms.star'
ODD_SUFFIX = '_odd'
EVEN_SUFFIX = '_even'
MASK_SUFFIX = '_mask'
MRC_EXT = '.mrc'

# Form parameters
IN_TOMOS = 'inTomos'
IN_CTF_SET = 'inCtfSet'
IN_TS_SET = 'inTsSet'
TOMO_MASKS = 'tomoMasks'
PREPARE_DATA_PROT = 'prepDataProt'

# CTF MODE
CTF_NONE=0
CTF_PHASE_ONLY=1
CTF_WIENER=2
CTF_NETWORK=3

# Architecture
UNET_SMALL=0
UNET_MEDIUM=1
UNET_LARGE=2

#Loss function
L1=0
HUBER=1
L2=2
