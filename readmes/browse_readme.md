# CH-1 M3 Browse Collection README file

## introduction

This collection contains browse products for the Chandraayan-1 (CH-1)
orbiter's Moon Mineralogy Mapper (M3). It consists of image files gathered
from the data volumes USA_NASA_PDS_CH1M3_0001, USA_NASA_PDS_CH1M3_0002, 
and USA_NASA_PDS_CH1M3_0003.

## naming conventions

### directories

The directory structure of this collection (relative to bundle root) is
``` 
/browse/(year)(month)/(year)(month)(day)
```

Dates are Gregorian UTC.

### files

We have retained the original archivists' "basename" convention for these
products' file names and their LIDs. The pattern for browse file names is:

```
m3(mode)(year)(month)(date)t(hour)(minute)(second)_(file suffix)
```

* "mode" can have values "g" or "t." It indicates whether M3 was in global or
target mode during data acquisition (see the catalog and SIS files in the
document collection for a description of these modes).  
* all times are UTC.
* times give the starting time of an observation.
* see below for file suffixes.

For example: m3g20090816t005433_albedo.xml is a label for an albedo-band
browse image taken from a global-mode L0 observation acquired starting at
00:54:33 UTC on August 16, 2009. It can be found in this bundle at
/browse/200908/20090816/m3g20090816t005433_albedo.xml.


### basename relationships

The "basename" of a file (the part up to the first underscore) is shared
across  data sets and implies relationships between products. For instance,
m3g20090816t005433_browse_46.jpg is derived from the data represented in the
observational data files m3g20090816t005433_l0.fits,
m3g20090816t005433_l1b_rdn.fits, and m3g20090816t005433_l2_rfl.fits.

## browse file format

### overview

Browse images are described in the EXTRINFO.TXT files in the PDS3 archive as
"a single-band albedo JPEG image ([...]B046.JPG) and a single-band thermal
JPEG image ([...]B084.JPG) for each M3 radiance image cube". The numbers
before the filename extension presumably refer to the band / channel number
from which they were produced. This accurately describes the JPEGs that match
global-mode observations, but each target-mode observation in fact has four
JPEGs, from bands 46, 84, 105, and 250. We have called the lower three bands
'albedo' for target-mode observations. M3 had higher spectral resolution in
target mode than in global mode, so the same channel numbers do not correspond
to the same physical wavelengths in both modes. See m3g20081211_rdn_spc.tab
and m3t20070912_rdn_spc.tab in the /document/calibration directory of this
bundle for canonical center wavelengths for each band in global and target
mode respectively.

No details on the production of these images were provided by the original
archivists. We have retained them as-is with modified filenames and PDS4
labels. **Warning:** we have not verified that these browse images in fact
correspond to the implied bands of their source data, nor confirmed how 
they might have been extracted from the calibrated data (or even, with 
certainty, that they were produced from data that had been calibrated). We 
caution users strongly against using these images for any science-quality 
analysis.

### global mode

There are four browse files associated with each global-mode observation:

```
(basename)_albedo.xml
```
PDS4 label for the 'albedo' browse image.

```
(basename)_albedo_46.jpg
```
The 'albedo' browse image, from global mode band 46 (about 1490 nm). 

```
(basename)_thermal.xml
```
PDS4 label for the 'thermal' browse image.

```
(basename)_thermal_84.jpg
```
The 'thermal' browse image, from global mode band 84 (about 2940 nm).


### target mode

There are six browse files associated with each target-mode observation:

```
(basename)_albedo.xml
```
PDS4 label for the 'albedo' browse images.

```
(basename)_albedo_46.jpg
```
The first 'albedo' browse image, from target mode band 46 (about 850 nm).

```
(basename)_albedo_84.jpg
```
The second 'albedo' browse image, from target mode band 84 (about 1230 nm).

```
(basename)_albedo_105.jpg
```
The third 'albedo' browse image, from target mode band 105 (about 1440 nm).

```
(basename)_thermal.xml
```
PDS4 label for the 'thermal' browse image.

```
(basename)_thermal_250.jpg
```
The 'thermal' browse image, from target mode band 250 (about 2890 nm).
