# CH-1 M3 Data Collection README file

## introduction

This collection contains observational products from the Chandraayan-1 (CH-1)
orbiter's Moon Mineralogy Mapper (M3). It is essentially a conversion and
reorganization of observational data from the PDS3 data sets
CH1-ORB-L-M3-2-L0-RAW-V1.0, CH1-ORB-L-M3-4-L1B-RADIANCE-V3.0, and
CH1-ORB-L-M3-4-L2-REFLECTANCE-V1.0. All images in this archive were acquired 
from lunar orbit during CH-1's primary mission phase, beginning in November
2008 and ending (prematurely) in August 2009.

This document provides a brief description of the organization and format of
these observational products, along with some notes on how they differ from the
contents of their source data sets.

## naming conventions

### directories

The directory structure of this collection (relative to bundle root) is
``` 
/data/(data set)/(year)(month)/(year)(month)(day)
```
* "data set" can have values "l0", "l1b", or "l2".  
* dates are Gregorian UTC.

### files

We have retained the original archivists' "basename" convention for these
products' file names and their LIDs, although we have converted it to lower case
to help visually distinguish these files from versions from the previous archive
that users might have on hand. The pattern for observational data file names is:

```
m3(mode)(year)(month)(date)t(hour)(minute)(second)_(data set)_(file extensions)
```

* "mode" can have values "g" or "t." It indicates whether M3 was in global or
target mode during data acquisition (see the catalog and SIS files in the
document collection for a description of these modes).  
* "data set" can have values "l0", "l1b", or "l2".  
* see individual directory descriptions below for a full list of file extensions. 
* all times are UTC.
* times give the starting time of an observation.

For example: m3g20090816t005433_l0.fits is a global-mode L0 image acquired
starting at 00:54:33 UTC on August 16, 2009. It can be found in this bundle at
/data/l0/200908/20090816/m3g20090816t005433_l0.fits.

### basename relationships

The "basename" of a file (the part up to the first underscore) is shared
across data sets and implies a relationship between products. For instance:
m3g20090816t005433_l1b_rdn.fits and m3g20090816t005433_l2_rfl.fits (along with 
their ancillary files) are increasingly reduced from m3g20090816t005433_l0.fits:
m3g20090816t005433_l0.fits 
	-> m3g20090816t005433_l1b_rdn.fits 
		-> m3g20090816t005433_l2_rfl.fits.

Every file in a reduced (L1B or L2) data set is a component of a full
trio of products: L0, L1B, and L2. However, not all observations were reduced,
so many L0 products have no corresponding L1B or L2 products.

Calibration files also share basenames with the observational products they were
used to calibrate, and browse files share basenames with their source
observational products; see descriptions in /document/document_readme.md and
/browse/browse_readme.md for details.

## file formats

### L0

Each L0 product in this bundle consists of three files (including the label):

```
(basename)_l0.xml
```
PDS4 label for the product.

```
(basename)_l0.fits
```
The observation itself: an uncalibrated multispectral image in units of DN (raw
detector count). The originally-archived versions of these files are in a
deprecated ENVI format that includes timing information in a binary line prefix
table (an "interleaved" table with entries at the beginning of each line). We
have detached these tables as ASCII CSV files and reformatted the images as 3D
FITS arrays.


```
(basename)_l0_clock_table.csv
```
Table giving timing information, originally encoded as a binary line prefix
table in the image array, detached and formatted as ASCII CSV. Each column of
this CSV file corresponds to an individual bit of the original table. A detailed
description of the meanings of these values can be found in the document
collection of this bundle (/document/core/m3_l0_time_decoding.txt). Please note
that not all the line prefixes follow the standard given in mission
documentation. In particular, we found that some, but not all, L0 files also had
additional ASCII text in the prefix area of some lines. We could find no
format specification for this text, and so simply placed it, when present, in an
additional column of these tables.

### L1B

Each L1B product in this bundle consists of five files (including the label):

```
(basename)_l1b.xml
```
PDS4 label for the product.


```
(basename)_l1b_rdn.fits
```
The observation itself: a radiometrically calibrated multispectral image in 
units of W/m^2/sr/μm. ("rdn" = "radiance.") The originally-archived versions of
these files are in ENVI format with detached headers. We have reformatted them
as 3D FITS arrays; they are otherwise unchanged. 


```
(basename)_l1b_loc.fits
```
Selenographic location information for the observation encoded as a 3D array.
The three "bands" (axis 1) of these files have units of selenographic Longitude
(deg), Latitude (deg), Radius (m) respectively, in the MOON_ME coordinate
system. The originally-archived versions of these files are in ENVI format with
detached headers. We have reformatted them as 3D FITS arrays; they are otherwise
unchanged.


```
(basename)_l1b_obs.fits
```
Geometry information for the observation encoded as a 3D array. The ten "bands"
(axis 1) of these files have the following units, in order: 
1. to-sun azimuth angle (decimal degrees, clockwise from local north) 
2. to-sun zenith angle (decimal degrees, zero at zenith) 
3. to-sensor azimuth angle (decimal degrees, clockwise from local north) 
4. to-sensor zenith angle (decimal degrees, zero at zenith) 
5. observation phase angle (decimaldegrees, in plane of to-sun and to-sensor rays) 
6. to-sun path length (decimal au with scene mean subtracted) 
7. to-sensor path length (decimal meters) 
8. surface slope from DEM (decimal degrees, zero at horizontal) 
9. surface aspect from DEM (decimal degrees, clockwise from local north) 
10. local cosine i (unitless, cosine of angle between to-sun and local DEM facet
normal vectors)
The originally-archived versions of these files are in ENVI format with
detached headers. We have reformatted them as 3D FITS arrays; they are otherwise
unchanged.

```
(basename)_l1b_tim.tab
```
Detailed timing table for the observation. We have slightly modified these
tables to conform to PDS4 standards for specifying UTC time data. 


### L2 

Each L2 product in this bundle consists of three files (including the label):


```
(basename)_l2.xml
```
PDS4 label for the product.


```
(basename)_l2_rfl.fits
```
The observation itself: a thermally and photometrically corrected multispectral
image given in unitless albedo values. 1.0 represents 100% reflectance. ("rfl" =
"reflectance.")The originally-archived versions of these files are in ENVI
format with detached headers. We have reformatted them as 3D FITS arrays; they
are otherwise unchanged. 

```
(basename)_l2_sup.fits
```
Ancillary information for the observation given as a 3D array. The three "bands"
(axis 1) of the array contain:
1. 1489-nm photometrically-corrected albedo, 
2. temperature estimated and applied by the thermal correction step of the L2 
    calibration process. 
3. Longest wavelength band that is 'scientifically useful" and has topography 
   (number 84 for global mode or 253 for target) from the associated L1B 
   radiance image.

Array values in band 1 are unitless quantities; 1.0 represents 100% 
reflectance. Band 2 is in Kelvin. Band 3 is in W/m^2/sr/μm.

The originally-archived versions of these files are in ENVI format with detached
headers. We have reformatted them as 3D FITS arrays; they are otherwise
unchanged. 

**NOTE TO REVIEWERS / CURATING FACILITY:**

*We suspect that, across much of the archive, the above description (taken from
the format specification and labels in the PDS3 archive) is wrong. Band 1 often
appears to contain radiance values; Band 3 often appears to contain reflectance
values. However, we have not rigorously investigated this across the whole archive.
We leave it up to you to decide whether to change the band descriptions here and
in the labels. --Million Concepts*

## additional notes

### versioning

The PDS holds three versions of the M3 L1B data set. All L1B products in this
collection are based on version 3 (CH1-ORB-L-M3-4-L1B-RADIANCE-V3.0). Versions 1
and 2 had calibration errors corrected by a procedure the instrument team
referred to as 'SSC_ADJ," as well as an indexing error that caused line
mismatches between images and their ancillary files. (See the discussion of
'smooth shape curves" in /document/document_readme.md, the curves themselves in
the /document/calibration/smooth_shape_curve directory, and pp. 33-36 of the
DPSIS  for more detail.) To avoid confusion, we have not produced new versions
of version 1 or 2 L1B products. To our knowledge, there are no other publicly-
available versions of the L0 or L2 data sets.

### image orientation

The instrument team corrected L1B and L2 products for orbit direction and
spacecraft orientation, so they may appear horizontally and/or vertically
mirrored with respect to their L0 source images. We have chosen to follow the
instrument team's decision to specify left-to-right, top-to-bottom display
directions for all products and leave coregistration of L0 with L1B / L2
products up to users. Refer to their discussion on p.77 of the DPSIS, along with
the chan1:orbit_limb_direction and chan1:spacecraft_yaw_direction tags in the
PDS4 labels of these products. 

### possibly-incorrect target information

The PDS3 labels for all observational products claim that they target the Moon.
However, in at least some cases, this is wrong. For instance, files with
basenames m3g20090722t021504 and m3g20090722t022534 clearly contain observations
of the Earth. We have manually changed these, but have not exhaustively swept
the archive for other possibly-mislabeled products. We caution users that cases
in which the chan1:spacecraft_clock_start_count metadata attribute is recorded
as "UNK" (as in these products) may indicate that it is in some way out of the
main observational series and therefore mistargeted.

### unapplied calibration processes

Not all known errors and anomalies in the observational data, particularly those
discovered after the data were initially archived with the PDS in June 2010,
have been addressed in any publicly-available archive. Methods for correcting
some of them are provided by some of the calibration products included in this
bundle in /document/calibration and its subdirectories. See our discussion of
calibration products in /document/document_readme.md for details.