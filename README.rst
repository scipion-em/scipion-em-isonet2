=============================
Scipion plugin for Isonet2
=============================

.. image:: https://img.shields.io/pypi/v/scipion-em-isonet2.svg
        :target: https://pypi.python.org/pypi/scipion-em-isonet2
        :alt: PyPI release

.. image:: https://img.shields.io/pypi/l/scipion-em-isonet2.svg
        :target: https://pypi.python.org/pypi/scipion-em-isonet2
        :alt: License

.. image:: https://img.shields.io/pypi/pyversions/scipion-em-isonet2.svg
        :target: https://pypi.python.org/pypi/scipion-em-isonet2
        :alt: Supported Python versions

.. image:: https://img.shields.io/pypi/dm/scipion-em-isonet2
        :target: https://pypi.python.org/pypi/scipion-em-isonet2
        :alt: Downloads

This plugin provides a wrapper around the program
`Isonet2 <https://github.com/IsoNet-cryoET/IsoNet2/tree/main#212b-predict>`_ to use it within `Scipion <https://scipion-em.github.io/docs/release-3.0.0/index.html>`_ framework.
IsoNet2 uses deep learning to compensate for the missing wedge, CTF correction and to denoise cryo-electron tomograms, using the even/odd half tomograms (noise2noise).


Installation
------------

You will need to use `3.0 <https://scipion-em.github.io/docs/release-3.0.0/docs/scipion-modes/how-to-install.html>`_
version of Scipion to run these protocols. To install the plugin, you have two options:


a) Stable version:

.. code-block::

    scipion3 installp -p scipion-em-isonet2

b) Developer's version

    * download the repository from github:

    .. code-block::

        git clone -b devel https://github.com/scipion-em/scipion-em-isonet2.git

    * install:

    .. code-block::

        scipion3 installp -p /path/to/scipion-em-isonet2 --devel

To check the installation, simply run the following Scipion test for the plugin:

    .. code-block::

        scipion3 tests isonet2.tests.tests_isonet2.TestIsonet2

To check the installation, run the plugin tests. A complete list of tests can be displayed by executing

.. code-block::

    scipion3 tests --grep isonet2 --show


Protocols
-----------

The plugin provides 5 protocols: **prepare data**, **training**, **predict**, **make mask** and **refine**, and they
operate on a ``.star`` text file which records data paths and parameters.

* **Prepare data**: Prepares the first ``inTomograms.star`` file for the IsoNet2 pipeline from a set of tomograms with their even/odd halves, the tilt-series and the CTF estimation.
  It lists the tomogram halves paths and the acquisition metadata.

* **Training**: Noise-to-noise (n2n) training (denoising) of the IsoNet2 network on the prepared data that can optionally include CTF correction.
  A U-Net-based architecture network is trained to minimize the discrepancies between the two independent half-datasets derived from the even/odd halves.
  It provides a ``loss_full.png`` file that shows the model's learning progress over time during n2n training.

* **Predict**: Applies a trained model to the tomograms, producing denoised and/or missing-wedge corrected tomograms.
  The original ``inTomograms.star`` is updated with paths pointing to the denoised and/or missing-wedge corrected tomograms.

* **Make mask**: Generates masks from the tomograms to restrict the training to exclude empty/unwanted areas of each tomogram.
  They're not necessary for denoising.
  The ``inTomograms.star`` is updated with a path pointing to the masks.

* **Refine**: Trains the network to predict missing-wedge-corrected, CTF-corrected, and denoised tomograms.
  It provides a ``loss_full.png`` file that shows the model's learning progress over time, both in terms of n2n training and missing-wedge correction.

**Training**, **Predict** and **Refine** require GPU acceleration.


Pipeline
-----------

* The following pipeline produces denoised tomograms:
**Prepare Data** → **Training** → **Predict**

  The trained network model, saved as a ``.pt`` file, can be applied to the original tomograms or similar tomograms.

* The following pipeline produces missing-wedge corrected and denoised tomograms:
**Prepare Data** → **Training** → **Predict** → **Make mask** → **Refine** → **Predict**

  Make mask is an optional step to mask unwanted regions from the denoised tomograms. The refine network model, saved as
  a ``.pt`` file, can be applied to the original tomograms or similar tomograms.


Notes for the Scipion plugin
-----------

* CTF correction
  IsoNet2 corrects the CTF within the network training. The correction is controlled by the ``CTF mode`` parameter, available in the
  **Training** and **Refine** protocols:

  * ``None``: no CTF correction (IsoNet2 default).
  * ``phase_only``: phase-only correction.
  * ``network``: the network input is multiplied by the CTF, so that the network learns to
    compensate for it, analogous to the missing-wedge correction.
  * ``wiener``: a Wiener filter is applied to the network target. Only in this mode the
    ``SNR falloff``, ``Deconvolution strength`` and ``Highpass Nyquist`` parameters have an effect.

* Training of at least 50 epochs is recommended.
* Memory usage during training/refine can be reduce by: enabling mixed_precision for float16, reducing batch_size, choosing a smaller network architecture and reducing the cube_size
* In the **Refine** protocol, missing wedge reconstruction can be prioritized over denoising by setting higher values of `Missing wedge loss weight`.

Latest plugin versions
----------------------

If you want to check the latest version and release history go to `CHANGES <https://github.com/scipion-em/scipion-em-isonet2/blob/master/CHANGES.txt>`_

References
----------

Liu, YT., Zhang, H., Wang, H. et al. Isotropic reconstruction for electron tomography with deep learning. Nat Commun 13, 6482 (2022). https://doi.org/10.1038/s41467-022-33957-8


