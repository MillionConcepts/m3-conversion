# CH-1 M3 Document Collection README file

## introduction

This collection contains documentation products related to the Chandraayan-1
(CH-1) orbiter's Moon Mineralogy Mapper (M3) and its observational data.
It largely consists of files taken from the PDS3 data sets
CH1-ORB-L-M3-2-L0-RAW-V1.0, CH1-ORB-L-M3-4-L1B-RADIANCE-V3.0, and
CH1-ORB-L-M3-4-L2-REFLECTANCE-V1.0, some of which have been reformatted. This
collection includes both "documents" in the narrow sense of "descriptive texts"
and "documents" in the broader sense of "ancillary products that help
contextualize observational data," specifically geometry and calibration
files. This document gives an overview of the directory structure of this
collection and its included files, along with some notes on how users might 
best make use of them in order to understand the M3 corpus as a whole. Some of
the contents of this file partially duplicate descriptions from product labels.

**IMPORTANT:** some of the documents in this collection are wholly or partially
deprecated by the ways in which the M3 observational data has been reformatted
or reorganized in this bundle. Specific notes on these deprecations are
contained in this file (and individual product labels).

## general note on file formats

All of the FITS files in this collection were originally ENVI files with
detached headers. To improve usability and standardization, we converted them
to FITS format and discarded their detached headers. We have not otherwise
modified them.

Some documents in this collection originally included nonstandard character
encodings or PDF features. We converted them to UTF-8 or PDF/A as gently as
possible.

## directory listing

All paths are given relative to the root directory of the bundle. 

Every product in this collection consists of a single digital object contained
in a discrete file, and each label file in this collection shares a filename
root with the file that contains the object it labels. For these reasons,
labels are not described separately below.

### /document

Root directory of this collection.

#### document_readme.md

The file you are reading right now.

#### collection_document_inventory.csv

PDS4 inventory file for this collection.

----

### /document/calibration

This directory and its subdirectories contain files related to the mission's
calibration and reduction pipelines. A walkthrough of mission calibration
procedures can be found in the mission's Data Product Software Interface
Specification (DPSIS), included in this collection as
/document/core/dpsis.pdf. Many of the file summaries below also reference
pages in that document.

Please note that not all of the calibration procedures these files are
intended to enable have actually been applied to the data in this archive. In
particular, the data in this archive have not had crosstrack or ground truth
corrections applied to them and have not been reprocessed using the updated
F-of-Alpha values. See file summaries below for details.

This directory itself (as opposed to its subdirectories) contains
theoretically- or laboratory-derived "constant" files. Dates in these
filenames refer to the creation dates of the files.

#### global_bandpass_file.fits

Spectral filter response file. Original description: "global band passes made
by averaging target best-fit gaussians, then renormalizing to unit sum.
85 global bands (as columns) (global bands 1 to 85); 2701 wavelengths (as lines)
(1nm spacing 350 nm to 3050 nm)."

#### lab_flat_field_global.fits

This file contains the flat-field response for the detector in global mode.
See the DPSIS, p.30. 

#### lab_flat_field_target.fits

As above, but with the detector in target mode.

#### m3_detector_temperature.tab

Table providing a canonical detector temperature for every M3 observation.

#### m3g20081118_rdn_cal.tab

Global-mode spectral calibration file used in reduction of L0 to L1B data.
Gives conversion factors between DN (detector count) and radiance at each
channel.

#### m3t20081118_rdn_cal.tab

As above, but for target mode.

#### m3g20081211_rdn_gain.tab

Radiometric gain file used in reduction of L0 to L1B data. Labeled as a series
of per-channel multiplication factors. However, every value in the associated
table is 1. We suspect that this file may not have been archived correctly.

#### m3t20070912_rdn_gain.tab

As above, but for target mode (and again, every multiplication factor is 1).

#### m3g20081211_rdn_spc.tab

A spectral calibration table giving canonical center wavelengths for
each channel in global mode.

#### m3t20070912_rdn_spc.tab

As above, but for target mode; this table also gives FWHM for each channel /
bandpass.

#### m3g20110224_rfl_solar_spec.tab

Theoretically-derived solar spectrum interpolated to global-mode bandpasses. 

#### m3t20110224_rfl_solar_spec.tab

Theoretically-derived solar spectrum interpolated to target-mode bandpasses.

#### m3g20110830_rfl_stat_pol_1.tab

"statistical polisher" table (see the DPSIS, 44-47) for global mode during
"cold" periods: 2009 Jan 19 through 2009 Feb 14, 2009 Apr 15 through 2009 Apr
27, and 2009 Jul 12 through 2009 Aug 16.

#### m3g20110830_rfl_stat_pol_2.tab

"statistical polisher" table for global mode during "warm" periods: 2008 Nov
18 through 2009 Jan 18, 2009 May 13 through 2009 May 16, and 2009 May 20
through 2009 Jul 9.

#### m3t20111020_rfl_stat_pol_1.tab

"statistical polisher" table for target mode during "cold" periods.

#### m3t20111020_rfl_stat_pol_2.tab

"statistical polisher" table for target mode during "warm" periods.

#### m3g20111109_rfl_f_alpha_hil.tab

"This table provides F-of-Alpha photometric correction factors for global-mode
reflectance data. The factors are dependent on phase angle (alpha) and channel
(wavelength) [...] and were derived from highland data." (original
description)" **Note:** these photometric correction factors were later found
to produce some undesirable results, particularly in the 2500-3000 nm range,
but all of the archived data retain these erroneous factors.
m3g20120120_rfl_f_alpha_hil.tab is an updated version intended to replace
these factors after a user divides them back out of the L2 data (see the
DPSIS, 48-50, for a description of the photometric correction step of L2 data
reduction, though no method for reversing this correction is explicitly
discussed).

#### m3t20120120_rfl_f_alpha_hil.tab

As above, but for target mode.

#### m3g20120120_rfl_f_alpha_hil.tab

Corrected version of the global-mode F-of-Alpha table.

#### m3t20111109_rfl_f_alpha_hil.tab

Corrected version of the target-mode F-of-Alpha table.

#### m3g20111117_rfl_grnd_tru_1.tab

Global-mode ground truth correction file (see the DPSIS, 51-59) for "cold"
periods. **Note:** the ground truth correction step has **not** been applied
to any of the data archived in the PDS.

#### m3g20111117_rfl_grnd_tru_2.tab

Global-mode ground truth correction file for "warm" periods. 

#### m3t20111117_rfl_grnd_tru_1.tab

Target-mode ground truth correction file for "cold" periods. 

#### m3t20111117_rfl_grnd_tru_2.tab

Target-mode ground truth correction file for "warm" periods. 

#### m3g20120120_crosstrack_corr.tab

From the PDS3 label: "Investigation of mosaics derived from version 1.0 of the
Level 2 M3 archive delivered to PDS found they include boundaries between
images, which are not completely removed even after the photometric
corrections. [...] An empirical correction to reduce the cross-track effect
was derived by using the average residual of all version 1.0 Level 2 M3 data
archived in PDS. This table contains the resulting scalar values that can be
added to the Level 2 data to reduce the boundary differences between images.
The values do not change the mean reflectance of an image. This correction can
be used to improve mosaiced images; however it has only a small effect on the
spectra. This analysis is discussed in the paper "A Visible and Near-Infrared
Photometric Correction for the Moon Mineralogy Mapper (M3)" by Besse, et al.,
(2012)." This table is for global-mode data. **Note:** this correction has
**not** been applied to data in this archive.

#### m3t20120120_crosstrack_corr.tab

As above, but for target-mode data.

----

### /document/calibration/bad_detector_elements

This directory, in subdirectories organized by year and month, contains bad
detector maps used in reducing L0 to L1B data (see DPSIS, 28). They are
2D FITS arrays flagging detector elements that appear nonresponsive or overly
noisy during particular observations. These files have the naming pattern:
```
(basename)_bde.fits
```
Each such file corresponds to the set of observational data products with
which it shares its basename (see /data/data_readme.md for a description of 
the M3 basename convention). 

----

### /document/calibration/flat_field

This directory, in subdirectories organized by year and month, contains 2D
FITS arrays giving per-observation flat-field correction factors used in
reducing L0 to L1B data (see the DPSIS, 31). They have the naming
pattern:
```
(basename)_ff.fits
```
Each such file corresponds to the set of observational data products with
which it shares its basename (see /data/data_readme.md for a description of 
the M3 basename convention). 

----

### /document/calibration/smooth_shape_curve

This directory, in subdirectories organized by year and month, contains
empirically-derived spectral smoothing files used in L1B calibration (see the
DPSIS, 33-36). No labels or format specifications are given for these files,
so we have simply labeled them as text documents. However, it is likely that
they can be transparently interpreted as fixed-width tables giving correction
factors at each channel/bandpass.

They have the naming pattern:
```
(basename)_ssc.txt
```
Each such file corresponds to the set of observational data products with
which it shares its basename (see /data/data_readme.md for a description of 
the M3 basename convention). 

----

### /catalog

Renamed copies of PDS3 .CAT files from the original archive. These files
provide high-level overviews of important features of the mission, instrument,
archive, and associated concepts.

#### inst_cat.txt

Provides high-level information regarding the M3 instrument itself.

#### insthost_cat.txt

Provides high-level information regarding the CH-1 orbiter as a whole.

#### l0_ds_cat.txt

Provides high-level information regarding the L0 data set's contents.
**Warning:** some remarks regarding media, file formats, and directory structure
are deprecated in the PDS4 version of this archive. It nevertheless remains a
useful overview of the L0 data and the data providers' intentions, but do not 
take it as totally current.

#### l1b_ds_cat.txt

As above, but for the L1B data set.

#### l2_ds_cat.txt

As above, but for the L2 data set.

#### mission_cat.txt

Provides high-level information regarding the CH-1 mission as a whole.

#### person_cat.txt

Provides attribution and contact information for personnel and institutions
related to the PDS3 archive. **Warning:** no attempt has been made to verify
or update this list. Much of this contact information is likely out of date. 

#### ref_cat.txt

Provides a list of references to published literature regarding CH-1,
its M3, and related science and engineering topics.

----

### /core 

This subdirectory contains documents that the original archivists considered
central to description of the archive -- Software Interface Specification
(SIS) files, format descriptions, and so on.

#### dpsis.pdf

Final revision of the Data Product Software Interface Specification (DPSIS)
for the PDS3 M3 archive. **Warning:** its file format specifications and notes
on archive structure are deprecated by this PDS4 bundle. However, it remains
essential for understanding the M3 observational data corpus.

#### m3_l0_time_decoding.txt

Format description for L0 raw time data. **Warning:** this data is no longer
contained in binary line prefix tables. Each L0 observation now has a detached
.csv file containing this information; each column of those CSV files
corresponds to a "bit" as described in this file.

#### pds3_archsis.pdf

Final revision of the Archive SIS for the PDS3 version of the M3 archive.
**Warning:** this document is deprecated; this archive does not follow the
structure of that archive. It nevertheless provides valuable supplementary and
historical information.

#### pds3_l0_l1b_errata.txt

Change list and errata for the PDS3 L0 and L1B data sets. **Warning:** Most of
this document is deprecated; it is retained primarily for historical interest and
error tracing.

#### pds3_l2_errata.txt

As above, but for the L2 data set.

----

### /geometry

This subdirectory contains relevant SPICE kernels.

#### aig_ch1_sclk_complete_biased_m1p816.tsc

CH-1 SCLK file. Allows conversions between TDT and CH-1 clock from clock start
to 2010-12-31.

#### ch-1-jpl-merged-23-march-2010-1220.bsp

SPICE binary SPK ephemeris kernel for CH-1 ephemeris (S/C ID -86).

#### m3_target_mode_camera.ik

SPICE text IK instrument kernel for M3 Target Mode camera model and FOV.

----

### /publications

This subdirectory contains copies of several publications related to the archive.

#### lunar_constants_models.pdf

JPL memo D-32296, giving what are likely the specific constants and models
used by the M3 team.

#### lunar_coordinate_white_paper.pdf

2008 revision of a white paper on lunar coordinate systems.

#### m3_overview_article.pdf

JGR article providing a broad overview of M3 instruments, data, and
calibration.

#### measuring_moonlight.pdf

JGR article describing M3, its observational data, and its data processing
pipeline.

#### thermal_removal_article.pdf

JGR article describing a thermal background reduction technique used in M3's
data reduction pipeline.

----

### /reduction_pipeline_logs

These files are logging output from the JPL software "m3_igds_l0_v18.pl." No
format standard or detailed description for these files is provided in the
archive. They appear to be intended to record problems during depacketization
of raw telemetry, primarily incomplete frames due to compression failures or
packet loss. 

They have the naming pattern:
```
(basename)_log.txt
```
Each such file presumably corresponds to the set of observational data
products with which it shares its basename (see /data/data_readme.md for a
description of the M3 basename convention). 

### /tutorials

This directory contains slide decks from two presentations that help provide
context for the M3 data.

#### m3_data_tutorial_november_2011.pdf

Slides from presentation on M3 data, including a high-level overview of the
instrument and mission and some notes on data processing. **Warning:**
portions of this presentation on L0 line prefix data and archive directory
structure are deprecated in this PDS4 bundle. 

#### working_with_l1b_data.pdf

Slides from presentation on working with M3 L1B data, primarily in ENVI.
**Warning:** it refers to ENVI 4.5, which has been out of support for some
time, and we have made no attempt to verify whether or not the described
techniques work with current versions of ENVI.

### /unique_images

(Actually only one image, but other unusual images could go here, should
any be produced in the future.)

#### earth_view_image.fits

"Global mode earth-view observation as acquired on 22 July 2009. This image 
was acquired by pointing Chandrayaan-1 spacecraft in the Earth direction and
then sweeping the M3 pushbroom field-of-view across the Earth with a
spacecraft pitch maneuver. This image includes the Western Pacific region of
the Earth and was acquired coincident with a solar eclipse in the center of
the image." (Description from EXTRINFO.TXT in the PDS3 archive) This file did
not have a PDS3 label, but based on the original file name, the ENVI header,
and the general character of its contents, it appears to be a
radiometrically-calibrated image produced in basically the same way as the L1B
RDN images from the main observational series.
