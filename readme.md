# ch-1 m3 pds3 -> pds4 conversion software repository

## introduction

This repository contains software and ancillary materials used to translate
and modernize imaging data and metadata from the Chandrayaan-1 Moon Mineralogy
Mapper ("M3"). This conversion effort specifically the PDS3 data sets
CH1-ORB-L-M3-2-L0-RAW-V1.0, CH1-ORB-L-M3-4-L1B-RADIANCE-V3.0, and
CH1-ORB-L-M3-4-L2-REFLECTANCE-V1.0, all currently held by the Planetary Data
System (PDS) Imaging Node (IMG). This software was used to organize the
contents of these data sets into PDS4 products and convert some of their
component files into more compliant and/or usable formats.

**All contents of this repository should be regarded with skepticism. The 
products they were used to produce have not yet been reviewed by the PDS.
We will do our best to update this repository to reflect the results of PDS
peer review, but it should currently be regarded as preliminary.**

### purpose of this repository

This software is intended basically as an extension of the documentation
provided in the bundle. We consider this form of software-as-documentation
essential for understanding scientific data.<sup>[1](#footnote1)</sup> 
Because the PDS does not archive software<sup>[2](#footnote2)</sup> other than
source code narrowly intended to describe a particular algorithm (which this
is not), we have placed this repository on GitHub. It contains files necessary
to understand, replicate, correct, and modify most of our process of
converting these PDS3 data sets into a PDS4 bundle.

For this reason, we strongly recommend that anyone who produces new versions
of the Chandrayaan-1 Moon Mineralogy Mapper bundle and makes them publicly 
available also modify or fork this repository -- or at least clearly document 
what happened to the data products after they were processed by the software 
in this repository. Otherwise, thisrepository will no longer be useful 
documentation; it could even become misleading.

### tips for use

* We recommend using the Anaconda distribution of Python and creating a
```conda``` environment using the provided
[environment.yml](/src/environment.yml) file. 
* This software will work on macOS or Linux. We recommend that Windows users use
[Windows Subsystem for Linux](https://ubuntu.com/wsl), a virtualized Linux
environment produced by Microsoft.
* One "oddball" manually-converted product -- a large earth view image -- is
not included in this repository because it is too large to be stored on
GitHub. It can be readily converted by users following the method we use for
the other ENVI arrays referenced in the codebase. 
* This is not, and is not intended to be, a ready-to-go installable application
or general-purpose library. Users will likely need to make modifications for
their individual working environments. In some cases, notes on this are
included in comments or text blocks in individual files. 
 * This software has *absolutely not been tested with any users other than 
ourselves.* We are happy to provide advice, to receive bug reports on issues 
that may have occurred during software export and transcription that render 
it unusable for persons other than ourselves, and *especially* happy to receive 
reports on software behavior that may have mangled output data or metadata. 
Please file GitHub issues.

### what this repository is not / limitations of this repository

This repository is not a mirror of the output PDS4 bundle. The bundle is over
four terabytes in volume; GitHub is not an appropriate platform from which to
serve the archive. Users who simply wish to access data in the bundle should
go to IMG's servers: **TODO: LINK GOES HERE WHEN LIVE.** Similarly, this
repository is not a mirror of the input PDS3 data sets. PDS3 products to use
this software on can be found on [volumes CH1M3_0001 through CH1M3_0004 in
this directory](https://pds-imaging.jpl.nasa.gov/data/m3/), also hosted by
IMG.

It does not exhaustively explain every step of the conversion and labeling
process. This is primarily because much of the process took place manually.
Many products, primarily documents (in the broad sense of "documents," 
including calibration products) were unique and therefore not subject to 
systematic processing. In some cases, the software in this repository was used in
one-off ways to convert these products; most of these cases are included in
comments. This repository also does not offer a complete discursive
walkthrough of our thought processes, rationale, workflow, etc. 

It does not contain all peripheral enabling software, like scripts to transfer
/ mirror the archive, name directories, and so on. These scripts are highly 
environment-specific and were often subject to manual adjustment; they would
not be useful additions to this repository. Similarly, a small number of
products in the document collection were made using GUI office applications
such as Adobe Acrobat and LibreOffice; it is impossible to include methods to
exactly replicate these processes.

## directory of contents

### /readmes

Copies of our readme files from the bundle to provide context for this
software. The data and browse readmes can be considered informal 
specifications for the outputs of this software.

### /src

Jupyter Notebooks and enabling Python modules for producing new versions of 
the M3 data and metadata. More details are included in comments or 
Markdown cells within these modules and notebooks.

### /src/directories/m3

File indices used to help organize and generate files and metadata.

### /src/labels/m3 and subdirectories

Includes:
1. Templates used by ```converter.py``` and related modules to produce PDS4 labels.
2. Most of the "one-off" unique-product labels from the bundle; included for context.

### /src/pdr and subdirectories

A 'frozen' alpha fork of [```pdr```](https://github.com/MillionConcepts/pdr) 
specially modified for this project.

## other notes

### cautions on reuse of this software

You can do almost anything with this software that you like, subject only to
the extremely permissive terms of the [BSD 3-Clause License](LICENSE).
However, we recommend that you be very careful about doing so. All of this
software should be considered special-purpose, intended specifically to work
with the products in the CH-1 M3 bundle. In particular, it includes
'frozen' alpha forks of some currently-available and forthcoming software
projects, including [```pdr```](https://github.com/MillionConcepts/pdr) and
its submodule ```pdr.converter```. We strongly recommend that the release or
primary development versions of included software be used in preference to the
contents of this repository for any other projects. Versions here have been
modified and evaluated specifically to work on these data sets **and may be
catastrophically unsuitable for any other purpose.**

Some of this software may serve as separable utilities for purposes other than
converting versions of the products in these data sets, of course. If you find
useful nuggets or patterns, we are very happy for you. However, in general, we
recommend great caution if using it for applications outside of its intended
purpose.

### style 

These modules were designed to be used to quickly diagnose and correct
problems in processes that had never before been performed. They are optimized
to be rapidly 'messed with' and modified in REPL environments. They are highly
verbose, often use ```print()``` rather than or in addition to loggers, have
Jupyter Notebooks rather than non-interactive execution scripts, and so on.
Should you decide to convert the M3 PDS3 archive to PDS4 several dozen times
in a row, we recommend making different style decisions.

Also note that the notebooks here present only an example of how the 
conversion software might be used to iterate over the PDS3 archive, perhaps in
 parallel. These procedural execution steps should not be considered
'canonical' (unless they missed or duplicated some products!) If you repeat
or modify this process, we encourage you to optimize it in the way that makes
most sense for your operating environment. We often like running a bunch of
notebooks in parallel as "bulkheads": they silo points of failure in a large,
slow process operating on not-yet-fully understood data. Bugs can be fixed
without interrupting the whole shebang.<sup>[3](#footnote3)</sup>

We have some additional notes on performance considerations in some notebooks.

## authorship and acknowledgments

The contents of this repository were produced by [Million
Concepts](https://www.millionconcepts.com) under contract from the United
States Geological Survey. This document,<sup>[4](#footnote4)</sup> along with
most of the software and other materials in this repository, was written by
Michael St. Clair. ```pdr``` was created by Chase Million and predates this
project, although some portions of the fork included in this repository were
specifically written by Chase and Michael for this project. Adam Ianno also
made significant contributions to this project.


This software relies on too much other software to individually cite it all,
but we would like to specifically call attention to:

* the PlanetaryPy project, especially Ross Beyer's [```pvl```](https://github.com/planetarypy/pvl)
* [GDAL](https://github.com/OSGeo/gdal/blob/master/CITATION)
  * mostly as wrapped in [rasterio](https://rasterio.readthedocs.io/en/latest/)
* [NumPy](https://www.numpy.org)
* [AstroPy](https://github.com/astropy/)
* [Pandas](https://pandas.pydata.org/)

----

<a name="footnote1">1</a>: The Astrophysics Source Code Library provides [an
excellent bibliography of references](https://ascl.net/home/getwp/676) on
scientific software transmission and preservation. Alexandra Chassanoff and
Micah Altman's concept of ["curation as interoperability with the
future"](https://dspace.mit.edu/handle/1721.1/125435) is especially relevant
to our effort here.

<a name="footnote2">2</a>: See ["Policy on Software Archiving", PDS Management
Council,
2016.](https://pds.nasa.gov/datastandards/documents/policy/SoftwareArchivingPosition06082016.pdf)

<a name="footnote3">3</a>: Erlang would probably be good for this.

<a name="footnote4">4</a>: Note that this document is largely rehearsed, with
appropriate changes, in our [Clementine Imaging Bundle conversion
repository](https://github.com/MillionConcepts/clementine-conversion).

