# CH-1 M3 Bundle README file

## introduction

This bundle contains observational products, documentation, and ancillary data
related to the Chandraayan-1 (CH-1) orbiter's Moon Mineralogy Mapper (M3). All
observational data in this bundle were acquired during CH-1's primary mission
phase, beginning in November 2008 and ending (prematurely) in August 2009.

Users who are generally familiar with the M3 archive should proceed directly
to the collection readme files: /document/document_readme.md and
/data/data_readme.md. They contain discussions of collection structure,
descriptions of included file formats, and other assorted tidbits and caveats.

We suggest that users who are unfamiliar with CH-1 and M3 begin by examining
the mission, host, and instrument catalog files in /document/catalog/:
inst_cat.txt, insthost_cat.txt, and mission_cat.txt. (Please note that several
other files in that directory are partially deprecated by this archive.)

Overviews from the NSSDC and ISRO may also provide useful introductory
information:
https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=2008-052A
https://www.isro.gov.in/Spacecraft/chandrayaan-1

## sources

This bundle is a translation and modernization of the PDS3 data sets
CH1-ORB-L-M3-2-L0-RAW-V1.0, CH1-ORB-L-M3-4-L1B-RADIANCE-V3.0, and
CH1-ORB-L-M3-4-L2-REFLECTANCE-V1.0. It organizes the contents of these data
sets into PDS4 products and converts some of their component files into more
compliant and/or usable formats.

Further notes on differences between the contents and organization of this
bundle and those data sets are included in the collection readmes.

**NOTE TO REVIEWERS / CURATING FACILITY:**
*we leave it up to you to decide how and whether to reference / include conversion
software. We suggest something like: "For a full specification of the conversion
process, please refer to the conversion software itself, externally hosted
at..." --Million Concepts*