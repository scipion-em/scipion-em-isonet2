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


a) Stable version (not available yet):

.. code-block::

    scipion3 installp -p scipion-em-isonet2

b) Developer's version

    * download the repository from github:

    .. code-block::

        git clone -b devel https://github.com/scipion-em/scipion-em-isonet2.git

    * install:

    .. code-block::

        scipion3 installp -p /path/to/scipion-em-isonet2 --devel

To check the installation, run the plugin tests. A complete list of tests can be displayed by executing

.. code-block::

    scipion3 tests --grep isonet2 --show

Protocols
-----------
The plugin provides 5 protocols: **Prepare_Data**, **Training**, **Predict**, **Make_Mask** and **Refine**, and they
operate on a ``.star`` text file which records their corresponding output paths.

* **Prepare Data**: Prepares the first ``.star`` file for the IsoNet2 pipeline from a set of tomograms with their even/odd halves, the tilt-series and the CTF estimation.
It lists the tomograms halves paths and the acquisition metadata.

* **Training**: Noise-to-noise (n2n) training of the IsoNet2 network on the prepared data that can optionally include CTF correction.
A U-Net-based architecture network is trained to minimize the discrepancies between the two independent half-datasets derived from the even/odd halves.

* **Predict**: Applies a trained model to the tomograms, producing missing-wedge corrected and denoised tomograms.

* **Make mask**: Generates masks from the tomograms to restrict the training to exclude empty/unwanted areas of each tomogram.

* **Refine**: Train the network to predict missing-wedge-corrected, CTF-corrected, and denoised tomograms.

**Training**, **Predict** and **Refine** requires GPU acceleration.

Pipeline
-----------
* The following pipeline produces denoised tomograms:
**Prepare Data** -> **Training** -> **Predict**

The trained network model, saved as a .pt file, can be applied to the original tomograms or similar tomograms.

* The following pipeline produces missing-wedge corrected and denoised tomograms:
**Prepare Data** -> **Training** -> **Predict** -> **Make mask** -> **Refine** -> **Predict**

Make_mask is an optional step to mask unwanted regions from the denoised tomograms. The refine network model,saved as
a .pt file, can be applied to the original tomograms or similar tomograms.

Latest plugin versions
----------------------

If you want to check the latest version and release history go to `CHANGES <https://github.com/scipion-em/scipion-em-isonet2/blob/master/CHANGES.txt>`_


