import bz2
from collections import OrderedDict
import gzip
from operator import getitem
import os
import struct
import sys
from types import MappingProxyType
from typing import Any, MutableMapping
from zipfile import ZipFile

from astropy.io import fits as pyfits
import pds4_tools
import numpy as np
import pandas as pd
import pvl

# TODO: this module doesn't exist in Ross's pvl 1.x
from pvl._collections import PVLObject
import rasterio
from rasterio.errors import RasterioIOError


# import matplotlib.pyplot as plt # just for QA


def get_from(collection: MutableMapping, keys, default=None) -> Any:
    """
    toolz-style getter that will attempt both getattr and getitem (intended
    for named tuples nested inside of dicts, etc)
    (hierarchical list of keys, collection ->
    item of collection, possibly from a nested collection)
    """
    level = collection
    for key in keys:
        try:
            level = getitem(level, key)
        except (KeyError, IndexError, TypeError):
            try:
                level = getattr(level, key)
            except AttributeError:
                return default
    return level


def pvl_to_dict(labeldata):
    # Convert a PVL label object to a Python dict Deprecated because PVL
    # allows keywords to be repeated at the same depth, which is _not_
    # allowed in a dict(), so this function ends up clobbering information.
    data = {}
    if (
            (type(labeldata) == pvl._collections.PVLModule)
            or (type(labeldata) == pvl._collections.PVLGroup)
            or (type(labeldata) == pvl._collections.PVLObject)
    ):
        for k in labeldata.keys():
            data[k] = pvl_to_dict(labeldata[k])
    else:
        return labeldata
    return data


def filetype(filename):
    """Attempt to deduce the filetype based on the filename."""
    if ".IMG" in filename.upper():
        return "IMG"
    elif ".FITS" in filename.upper():
        return "FITS"
    elif ".DAT" in filename.upper():
        if os.path.exists(filename.replace(".DAT", ".LBL")):
            # PDS3 .DAT with detached PVL label
            return "PDS3DAT"
        else:
            # presumed PDS4 .DAT with detached xml label
            return "PDS4DAT"
    else:
        print(
            "*** Unsupported file type: [...]{end}".format(end=filename[-10:])
        )
        return "UNK"


def has_attached_label(filename):
    """Read the first line of a file to decide if it's a label."""
    with open(filename, "rb") as f:
        return "PDS_VERSION_ID" in str(f.readline())


def parse_attached_label(filename):
    """Parse an attached label of a IMG file."""
    # First grab the entries from the label that define how to read the label
    return pvl.load(filename, strict=False)


# with open(filename, "rb") as f:
#     for line_ in f:
#         line = line_.decode("utf-8").strip()  # hacks through a rare error
#         if "PDS_VERSION_ID" in line:
#             PDS_VERSION_ID = line.strip().split("=")[1]
#         if "RECORD_BYTES" in line:
#             RECORD_BYTES = int(line.strip().split("=")[1])
#         if "LABEL_RECORDS" in line:
#             if "<BYTES>" in line:
#                 # Convert pointer value to bytes like everything else
#                 LABEL_RECORDS = line.strip().split("=")[1].split()[0] * 8
#             else:
#                 LABEL_RECORDS = int(line.strip().split("=")[1])
#             break
# # Read the label and then parse it with PVL
# try:
#     with open(filename, "rb") as f:
#         return pvl.load(f.read(RECORD_BYTES * (LABEL_RECORDS)))
# except UnboundLocalError:
#     print("*** RECORD_BYTES not set??? ***")
#     return None
# except:
#     with open(filename, "rb") as f:
#         return pvl.load(f.read(RECORD_BYTES * (LABEL_RECORDS)), strict=False)


def find_pointers(label, parent_level=None, path=""):
    """
    function to look for file pointers in PDS3 labels.
    drills down one level into 'file area' / sublabels, i.e.,
    nested PVLObjects.

    TODO:
    some of this interface appears to have changed in Ross's pvl 1.x
    and the class reference may need to be modified.

    TODO:
    these are never nested more than one level deep, right?
    """
    pointers = []
    for key, value in label.items():
        if isinstance(value, PVLObject):
            # go down a level to look for pointers in 'file areas' &c
            pointers += find_pointers(value, key, path)
        elif key.startswith("^"):
            if isinstance(value, str):
                # break up nested pointers; "if string" ignores None
                # from default parent_level
                pointer_target = os.path.join(path, value)
            elif isinstance(value, pvl._collections.Units):
                # attempt to handle byte offsets in attached labels
                pointer_target = value.value
            elif isinstance(value, int) and ("FILE_RECORDS" in label.keys()):
                # attempt to handle file records offsets in attached labels
                pointer_target = value * label["FILE_RECORDS"]
            else:
                print("Warning: " + str(
                    value) + "can't be interpreted as a valid target for a pointer.")
                continue
            pointers.append(
                {
                    "object": [
                        string for string in [parent_level, key[1:]] if string
                    ],
                    "target": pointer_target,
                }
            )
    return pointers


def find_pvl_objects(label):
    """
    list of PVLObjects at top level of PDS3 label.
    or anything, I guess.

    TODO:
    some of this interface appears to have changed in Ross's pvl 1.x
    and the class reference may need to be modified.
    """
    objects = []
    for key, value in label.items():
        if isinstance(value, PVLObject):
            objects.append(key)
    return objects


def get_file_area(label, pointer):
    if isinstance(pointer, str):
        # if we just passed a function "IMAGE" or what-have-you,
        # empirically, as it were,
        # rather than having discovered terms in the label
        file_area = label[pointer]
        object_name = pointer
    else:
        # for nested keys: we have a list in a dict.
        # reach down and grab the nested 'sublabel'
        # or 'file area' in PDS4 parlance
        file_area = get_from(label, pointer["object"])
        # because first terms of pointer are at a higher level of nesting
        object_name = pointer["object"][-1]
    return file_area, object_name


def parse_label(filename, full=False):
    """Wraps forking paths for attached and detached PDS3 labels."""
    if filename.endswith(".fmt"):
        return pvl.load(filename, strict=False)
    if not has_attached_label(filename):
        if os.path.exists(filename[: filename.rfind(".")] + ".LBL"):
            label = pvl.load(filename[: filename.rfind(".")] + ".LBL")
        elif os.path.exists(filename[: filename.rfind(".")] + ".lbl"):
            label = pvl.load(filename[: filename.rfind(".")] + ".lbl")
        elif os.path.exists(filename[: filename.rfind(".")] + ".xml"):
            # TODO: Make label data format consistent between PDS3 & 4
            label = pds4_tools.read(
                filename[: filename.rfind(".")] + ".xml", quiet=True
            ).label.to_dict()
        else:
            print("*** Unable to locate file label. ***")
            return None
    else:
        label = parse_attached_label(filename)
    # TODO: This ugly conditional exists entirely to deal with Cassini data
    # which all seem to be returning zero-value images, so maybe it's wrong!
    if (not full) and ("UNCOMPRESSED_FILE" in label.keys()):
        if "COMPRESSED_FILE" in label.keys():
            if "ENCODING_TYPE" in label["COMPRESSED_FILE"].keys():
                if (
                        label["COMPRESSED_FILE"]["ENCODING_TYPE"]
                        == "MSLMMM-COMPRESSED"
                ):
                    return label
        return label["UNCOMPRESSED_FILE"]
    return label


def sample_types(SAMPLE_TYPE, SAMPLE_BYTES):
    """Defines a translation from PDS data types to Python data types.

    TODO: The commented-out types below are technically valid PDS3
        types, but I haven't yet worked out the translation to Python.
    """
    # NOTE: The byte depth of various data types is non-unique in PDS3

    return {
        "MSB_INTEGER": ">h",
        "INTEGER": ">h",
        "MAC_INTEGER": ">h",
        "SUN_INTEGER": ">h",
        "MSB_UNSIGNED_INTEGER": ">h" if SAMPLE_BYTES == 2 else ">B",
        "UNSIGNED_INTEGER": ">B",
        "MAC_UNSIGNED_INTEGER": ">B",
        "SUN_UNSIGNED_INTEGER": ">B",
        "LSB_INTEGER": "<h" if SAMPLE_BYTES == 2 else "<B",
        "PC_INTEGER": "<h",
        "VAX_INTEGER": "<h",
        "ASCII_INTEGER": "<h",
        "LSB_UNSIGNED_INTEGER": "<h" if SAMPLE_BYTES == 2 else "<B",
        "PC_UNSIGNED_INTEGER": "<B",
        "VAX_UNSIGNED_INTEGER": "<B",
        "IEEE_REAL": ">f",
        "FLOAT": ">f",
        "REAL": ">f",
        "PC_REAL": "<d" if SAMPLE_BYTES == 8 else "<f",
        "MAC_REAL": ">f",
        "SUN_REAL": ">f",
        "MSB_BIT_STRING": ">B",
    }[SAMPLE_TYPE]


# Possibly unused in PDS3: just park them here unless needed
#        'IEEE_COMPLEX': '>c',
#        'COMPLEX': '>c',
#        'MAC_COMPLEX': '>c',
#        'SUN_COMPLEX': '>c',

#        'PC_COMPLEX': '<c',

#        'MSB_BIT_STRING': '>S',
#        'LSB_BIT_STRING': '<S',
#        'VAX_BIT_STRING': '<S',


def get_data_types(filename):
    """Placeholder function for the fact that PDS3 can contain multiple
    types of data (e.g. an image and a header) which are defined by
    'pointers' in the label. This should be dealt with at some point.
    """
    for k in parse_label(filename).keys():
        if k.startswith("^"):
            print(k)


def data_start_byte(label, pointer):
    """Determine the first byte of the data in an IMG file from its pointer."""
    if type(pointer) is str:
        name_or_offset = label["^" + pointer]
    # for nested keys
    else:
        name_or_offset = get_from(
            label, [*pointer["object"][0:-1], "^" + pointer["object"][-1]]
        )
    if type(name_or_offset) is int:
        return label["RECORD_BYTES"] * (name_or_offset - 1)
    elif type(name_or_offset) is pvl._collections.Units:
        return name_or_offset.value - 1
    elif type(name_or_offset) is list:
        if type(name_or_offset[0]) is int:
            return name_or_offset[0]
        elif type(name_or_offset[-1]) is int:
            return label["RECORD_BYTES"] * (name_or_offset[-1] - 1)
        else:
            return 0
    elif type(name_or_offset) is str:
        return 0
    else:
        print("WTF?", name_or_offset)
        raise


def read_document(filename, label, pointer):
    """
    placeholder function. right now just: if open will decode it as Unicode, great, return the text;
    otherwise, return the bytes.
    """
    try:
        with open(filename) as file:
            return file.read()
    except UnicodeDecodeError:
        with open(filename, "rb") as file:
            return file.read()
    except FileNotFoundError:
        return "referenced document not found"


def image_props_list():
    return [
        "BYTES_PER_PIXEL",
        "start_byte",
        "DTYPE",
        "nrows",
        "ncols",
        "prefix_bytes",
        "prefix_cols",
        "BANDS",
        "pixels",
        "band_storage_type",
    ]


def get_image_props(dictionary):
    """
    convenience function
    grabs image properties from a dict -- perhaps locals() --
    to be passed into a different scope
    """
    return {prop: dictionary[prop] for prop in image_props_list()}


def generic_image_props(label, pointer):
    try:
        sublabel = get_file_area(label, pointer)
        file_area = sublabel[0]
    except (KeyError, TypeError):
        # print("*** IMG w/ old format attached label not currently supported.")
        # print("\t{fn}".format(fn=filename))
        print("No image data identified.")
        return None
    BYTES_PER_PIXEL = int(file_area["SAMPLE_BITS"] / 8)
    DTYPE = sample_types(file_area["SAMPLE_TYPE"], BYTES_PER_PIXEL)
    nrows = file_area["LINES"]
    ncols = file_area["LINE_SAMPLES"]

    if "LINE_PREFIX_BYTES" in file_area.keys():
        # print("Accounting for a line prefix.")
        prefix_cols = int(file_area["LINE_PREFIX_BYTES"] / BYTES_PER_PIXEL)
        prefix_bytes = prefix_cols * BYTES_PER_PIXEL
    else:
        prefix_cols = 0
        prefix_bytes = 0
    try:
        BANDS = file_area["BANDS"]
        band_storage_type = file_area["BAND_STORAGE_TYPE"]
    except KeyError:
        BANDS = 1
        band_storage_type = None
    pixels = nrows * (ncols + prefix_cols) * BANDS
    start_byte = data_start_byte(label, pointer)
    return get_image_props(locals())


def ch1_m3_l0_image_props(label):
    """
    image properties for Chandrayaan-1 M3 L0 images, from the label.
    """
    BYTES_PER_PIXEL = int(label["L0_FILE"]["L0_IMAGE"]["SAMPLE_BITS"] / 8)
    DTYPE = sample_types(
        label["L0_FILE"]["L0_IMAGE"]["SAMPLE_TYPE"], BYTES_PER_PIXEL
    )
    nrows = label["L0_FILE"]["L0_IMAGE"]["LINES"]
    ncols = label["L0_FILE"]["L0_IMAGE"]["LINE_SAMPLES"]
    prefix_bytes = int(label["L0_FILE"]["L0_IMAGE"]["LINE_PREFIX_BYTES"])
    prefix_cols = (
            prefix_bytes / BYTES_PER_PIXEL
    )  # M3 has a prefix, but it's not image-shaped
    BANDS = label["L0_FILE"]["L0_IMAGE"]["BANDS"]
    pixels = nrows * (ncols + prefix_cols) * BANDS
    start_byte = 0
    band_storage_type = label["L0_FILE"]["L0_IMAGE"]["BAND_STORAGE_TYPE"]
    return get_image_props(locals())


def check_special_image_case(label, pointer):
    try:
        if (
                label["INSTRUMENT_ID"] == "M3"
                and label["PRODUCT_TYPE"] == "RAW_IMAGE"
        ):
            # print('Special case: Chandrayaan-1 M3 data.')
            return ch1_m3_l0_image_props(label)
        # if, if, if, special cases ad nauseam
    except KeyError:
        pass
    return False


def read_image(target, label, pointer="IMAGE"):  # ^IMAGE
    """Read a PDS IMG formatted file into an array.
    TODO: Check for and account for LINE_PREFIX.
    TODO: Check for and apply BIT_MASK.

    rasterio will read an ENVI file if the HDR metadata is present...
    However, it seems to read M3 L0 images incorrectly because it does
    not account for the L0_LINE_PREFIX_TABLE. So I am deprecating
    the use of rasterio until I can figure out how to produce consistent
    output.
    try:
        dataset = rasterio.open(filename)
        if len(dataset.indexes)==1:
            return dataset.read()[0,:,:] # Make 2D images actually 2D
        else:
            return dataset.read()
    except rasterio.errors.RasterioIOError:
        #print(' *** Not using rasterio. ***')
        pass
    """
    # TODO:
    # this should maybe always go in map_object_to_function,
    # but I'm not sure if read_image might want to get called
    # from other places that don't call that first.
    # probably best to check /decide this.
    # --Michael

    special_case = check_special_image_case(label, pointer)
    if special_case:
        props = special_case
    else:
        props = generic_image_props(label, pointer)

    # commented-out block here should work but it instead produces massive
    # quantities of bad spookiness. it specifically doesn't work
    # with certain variable names, variables pop in and out of existence,
    # somehow we hit undefined behavior:

    # read_image_namespace = locals()
    # for prop in image_props_list():
    #     read_image_namespace[prop] = props[prop]

    BYTES_PER_PIXEL = props["BYTES_PER_PIXEL"]
    start_byte = props["start_byte"]
    DTYPE = props["DTYPE"]
    nrows = props["nrows"]
    ncols = props["ncols"]
    prefix_bytes = props["prefix_bytes"]
    prefix_cols = props["prefix_cols"]
    BANDS = props["BANDS"]
    pixels = props["pixels"]
    band_storage_type = props["band_storage_type"]

    object_name = get_file_area(label, pointer)[1]

    # for attached labels, just point to the file
    # (which we should have assigned to a special key in the label)
    if isinstance(target, int):
        filename = label["attached_label_filename"]
    # otherwise point to the pointer target
    else:
        filename = target

    # a little decision tree to seamlessly deal with compression
    if filename.endswith(".gz"):
        f = gzip.open(filename, "rb")
    elif filename.endswith(".bz2"):
        f = bz2.BZ2File(filename, "rb")
    elif filename.endswith(".ZIP"):
        f = ZipFile(filename, "r").open(
            ZipFile(filename, "r").infolist()[0].filename
        )
    else:
        f = open(filename, "rb")
    # Make sure that single-band images are 2-dim arrays.
    f.seek(start_byte)
    # TODO: I don't know what the band-sequential case should look
    #  like, because I don't have test data rn, but I suspect it should be
    #  rewritten to look like the line-interleaved case. --Michael
    if BANDS == 1:
        fmt = "{endian}{pixels}{length}".format(
            endian=DTYPE[0], pixels=pixels, length=DTYPE[-1]
        )
        image = np.array(
            struct.unpack(fmt, f.read(pixels * BYTES_PER_PIXEL))
        ).reshape(nrows, ncols + prefix_cols)
        if prefix_cols:
            # Ignore the prefix data, if any.
            # TODO: Also return the prefix
            prefix = image[:, :prefix_cols]
            if object_name == "LINE_PREFIX_TABLE":
                return prefix
            image = image[:, prefix_cols:]
    elif band_storage_type == "BAND_SEQUENTIAL":
        raise NotImplemented("BAND_SEQUENTIAL presently not implemented")
        # pixels_per_frame = BANDS * nrows
        # fmt = "{endian}{pixels}{length}".format(
        #     endian=DTYPE[0], pixels=pixels_per_frame, length=DTYPE[-1]
        # )
        # image = np.array(
        #     struct.unpack(fmt, f.read(pixels * BYTES_PER_PIXEL))
        # )
        # image = image.reshape(BANDS, nrows)
    elif band_storage_type == "LINE_INTERLEAVED":
        pixels_per_frame = BANDS * ncols
        fmt = "{endian}{pixels}{length}".format(
            endian=DTYPE[0], pixels=pixels_per_frame, length=DTYPE[-1]
        )
        image, prefix = [], []
        for _ in np.arange(nrows):
            prefix.append(f.read(prefix_bytes))
            frame = np.array(
                struct.unpack(
                    fmt, f.read(pixels_per_frame * BYTES_PER_PIXEL)
                )
            ).reshape(BANDS, ncols)
            image.append(frame)
            del frame
        image = np.swapaxes(
            np.stack([frame for frame in image], axis=2), 1, 2
        )
    else:
        raise ValueError(f"Unknown BAND_STORAGE_TYPE={band_storage_type}")

    if f:
        f.close()
    if "PREFIX" in object_name:
        return prefix, image
    return image


def read_line_prefix_table(filename, label, pointer="LINE_PREFIX_TABLE"):
    return read_image(filename, label, pointer=pointer)


def read_CH1_M3_L0_prefix_table(filename, label, pointer):
    prefix, image = read_line_prefix_table(filename, label, pointer=pointer)
    return [
               [p[:269].decode("ascii")] + list(
                   struct.unpack("<22B", p[640:662]))
               for p in prefix
           ], image


def parse_image_header(filename, label):
    # Backup function for parsing the IMAGE_HEADER when pvl breaks
    with open(filename, "r") as f:
        f.seek(data_start_byte(label, "^IMAGE_HEADER"))
        header_str = str(f.read(label["IMAGE_HEADER"]["BYTES"]))
    image_header = {}
    lastkey = None
    for entry in header_str.split("  "):
        pv = entry.split("=")
        if len(pv) == 2:
            # The `strip("'")` is to avoid double quotations
            image_header[pv[0]] = pv[1].strip("'")
            lastkey = pv[0]
        elif len(pv) == 1 and lastkey:
            # Append the runon line to the previous value...
            if len(pv[0]):  # ... unless it's empty
                image_header[lastkey] += " " + pv[0].strip("'")
        else:
            raise
    return image_header


def read_image_header(filename, label):  # ^IMAGE_HEADER
    # label = parse_label(filename)
    try:
        with open(filename, "rb") as f:
            f.seek(data_start_byte(label, "^IMAGE_HEADER"))
            image_header = pvl.load(
                f.read(label["IMAGE_HEADER"]["BYTES"]), strict=False
            )
        return image_header
    except:  # Specifically on ParseError from PVL...
        # The IMAGE_HEADER is not well-constructed according to PVL
        try:  # to parse it naively
            return parse_image_header(filename, label)
        except:
            #  Naive parsing didn't work...
            #    so just return the unparsed plaintext of the image header.
            with open(filename, "r") as f:
                f.seek(data_start_byte(label, "^IMAGE_HEADER"))
                image_header = str(f.read(label["IMAGE_HEADER"]["BYTES"]))
            return image_header


def read_bad_data_values_header(filename):  # ^BAD_DATA_VALUES_HEADER
    label = parse_label(filename)
    with open(filename, "rb") as f:
        f.seek(data_start_byte(label, "^BAD_DATA_VALUES_HEADER"))
        bad_data_values_header = f.read(
            label["BAD_DATA_VALUES_HEADER"]["BYTES"]
        )
    print(
        "*** BAD_DATA_VALUES_HEADER not parsable without file: {DESCRIPTION} ***".format(
            DESCRIPTION=label["BAD_DATA_VALUES_HEADER"]["^DESCRIPTION"]
        )
    )
    return bad_data_values_header


def read_histogram(target, label=None, pointer="HISTOGRAM"):  # ^HISTOGRAM
    if label is None:
        label = parse_label(target)
    if isinstance(target, int):
        filename = label['attached_label_filename']
    else:
        filename = target
    file_area = get_file_area(label, pointer)[0]
    DTYPE = sample_types(file_area["DATA_TYPE"], 0)
    if file_area["ITEM_BYTES"] == 4:
        DTYPE = DTYPE[0] + "i"
    items = file_area["ITEMS"]
    fmt = "{endian}{items}{fmt}".format(
        endian=DTYPE[0], items=items, fmt=DTYPE[-1]
    )
    with open(filename, "rb") as f:
        f.seek(data_start_byte(label, pointer))
        histogram = np.array(
            struct.unpack(
                fmt, f.read(items * file_area["ITEM_BYTES"])
            )
        )
    return histogram


def read_engineering_table(filename, label):  # ^ENGINEERING_TABLE
    return read_table(filename, label, pointer="ENGINEERING_TABLE")


def read_measurement_table(filename, label):  # ^MEASUREMENT_TABLE
    return read_table(filename, label, pointer="MEASUREMENT_TABLE")


def read_telemetry_table(filename, label):  # ^TELEMETRY_TABLE
    return read_table(filename, label, pointer="TELEMETRY_TABLE")


def read_spectrum(filename):  # ^SPECTRUM
    print("*** SPECTRUM data not yet supported. ***")
    return


def read_jp2(filename):  # .JP2 extension
    # NOTE: These are the huge HIRISE images. It might be best to just
    #       leave the capability to GDAL so that we don't have to bother
    #       with memory management.
    print("*** JP2 filetype not yet supported. ***")
    return


def read_mslmmm_compressed(filename):
    """WARNING: Placeholder functionality.
    This will run `dat2img` to decompress the file from Malin's bespoke
    image compression format (which has no obvious purpose other than
    obfuscation) into the local direction, then read the resulting file,
    and then delete it.
    TODO: Modify dat2img.c and pdecom_msl.c, or port them, to decode the
        data directly into a Python array.
    """
    _ = os.system(f"./MMM_DAT2IMG/dat2img {filename}")
    imgfilename = filename.split("/")[-1].replace(".DAT", "_00.IMG")
    if os.path.exists(imgfilename):
        image = read_image(imgfilename)
        print(f"Deleting {imgfilename}")
        os.remove(imgfilename)
    else:
        print(f"{imgfilename} not present.")
        print("\tIs MMM_DAT2IMG available and built?")
    return


def read_fits(filename, dim=0, quiet=True):
    """Read a PDS FITS file into an array.
    Return the data _and_ the label.
    """
    hdulist = pyfits.open(filename)
    data = hdulist[dim].data
    header = hdulist[dim].header
    hdulist.close()
    return (
        data,
        pds4_tools.read(
            filename.replace(".fits", ".xml"), quiet=True
        ).label.to_dict(),
    )


def read_dat_pds4(filename, write_csv=False, quiet=True):
    """Reads a PDS4 .dat format file, preserving column order and data type,
    except that byte order is switched to native if applicable. The .dat file
    and .xml label must exist in the same directory.
    Return the data _and_ the label.
    """
    if filename[-4:].lower() == ".dat":
        filename = filename[:-4] + ".xml"
    if filename[-4:].lower() != ".xml":
        raise TypeError("Unknown filetype: {ext}".format(ext=filename[-4:]))
    structures = pds4_tools.pds4_read(filename, quiet=quiet)
    dat_dict = OrderedDict({})
    for i in range(len(structures[0].fields)):
        name = structures[0].fields[i].meta_data["name"]
        dat_dtype = structures[0].fields[i].meta_data["data_type"]
        dtype = pds4_tools.reader.data_types.pds_to_numpy_type(dat_dtype)
        data = np.array(structures[0].fields[i], dtype=dtype)
        if (sys.byteorder == "little" and ">" in str(dtype)) or (
                sys.byteorder == "big" and "<" in str(dtype)
        ):
            data = data.byteswap().newbyteorder()
        dat_dict[name] = data
    dataframe = pd.DataFrame(dat_dict)
    if write_csv:
        dataframe.to_csv(filename.replace(".xml", ".csv"), index=False)
    return dataframe


def read_dat_pds3(filename):
    if not has_attached_label(filename):
        print("*** DAT w/ detached PDS3 LBL not currently supported.")
        try:
            et = parse_label(filename)["COMPRESSED_FILE"]["ENCODING_TYPE"]
            print("\tENCODING_TYPE = {et}".format(et=et))
        except:
            pass
    else:
        print("*** DAT w/ attached PDS3 LBL not current supported.")
    print("\t{fn}".format(fn=filename))
    return None, None


def dat_to_csv(filename):
    """Converts a PDS4 file to a Comma Separated Value (CSV) file with
    the same base filename. The .dat file and .xml label must exist in
    the same directory.
    """
    _ = read_dat_pds4(filename, write_csv=True)


def unknown(filename):
    print("\t{fn}".format(fn=filename))
    return None, None


def read_abdr_table(filename):  # ^ABDR_TABLE
    print("*** ADBR_TABLE not yet supported. ***")
    return


def read_array(filename):  # ^ARRAY
    print("*** ARRAY not yet supported. ***")
    return


def read_vicar_header(filename):  # ^VICAR_HEADER
    print("*** VICAR_HEADER not yet supported. ***")
    return


def read_vicar_extension_header(filename):  # ^VICAR_EXTENSION_HEADER
    print("*** VICAR_EXTENSION_HEADER not yet supported. ***")
    return


def read_history(filename):  # ^HISTORY
    print("*** HISTORY not yet supported. ***")
    return


def read_spectral_qube(filename):  # ^SPECTRAL_QUBE
    print("*** SPECTRAL_QUBE not yet supported. ***")
    return


def read_spacecraft_pointing_mode_desc(
        filename,
):  # ^SPACECRAFT_POINTING_MODE_DESC
    print("*** SPACECRAFT_POINTING_MODE_DESC not yet supported. ***")
    return


def read_odl_header(filename):  # ^ODL_HEADER
    print("*** ODL_HEADER not yet supported. ***")
    return


def read_label(filename):
    try:
        label = pvl.load(filename, strict=False)
        if not len(label):
            raise ValueError("Cannot find attached label data.")
        label.append("attached_label_filename", filename)
        return label
    except:  # look for a detached label
        if os.path.exists(filename[: filename.rfind(".")] + ".LBL"):
            return pvl.load(
                filename[: filename.rfind(".")] + ".LBL", strict=False
            )
        elif os.path.exists(filename[: filename.rfind(".")] + ".lbl"):
            return pvl.load(
                filename[: filename.rfind(".")] + ".lbl", strict=False
            )
        else:
            print(" *** Cannot find label data. *** ")
            raise


def read_file_name(filename, label, pointer):  # ^FILE_NAME
    return label["^FILE_NAME"]


def read_description(filename, label, pointer):  # ^DESCRIPTION
    return label["^DESCRIPTION"]


def parse_table_structure(label, pointer="TABLE"):
    # Try to turn the TABLE definition into a column name / data type array.
    # Requires renaming some columns to maintain uniqueness. Also requires
    # unpacking columns that contain multiple entries. if
    # pointer=="TELEMETRY_TABLE": if ((label["SPACECRAFT_NAME"] == "GALILEO
    # ORBITER") and (label["INSTRUMENT_NAME"] == "SOLID_STATE_IMAGING")):
    # label = {pointer:parse_label(
    # 'ref/GALILEO_ORBITER/SOLID_STATE_IMAGING/rtlmtab.fmt')}
    file_area = get_file_area(label, pointer)[0]
    dt = []
    for obj in file_area:
        if obj[0] == "COLUMN":
            if obj[1]["NAME"] == "RESERVED":
                name = "RESERVED_" + str(obj[1]["START_BYTE"])
            else:
                name = obj[1]["NAME"]
            try:  # Some "columns" contain a lot of columns
                for n in range(obj[1]["ITEMS"]):
                    dt += [
                        (
                            f"{name}_{n}",
                            sample_types(
                                obj[1]["DATA_TYPE"], obj[1]["ITEM_BYTES"]
                            ),
                        )
                    ]
            except KeyError:
                if len(dt):
                    while (
                            name in np.array(dt)[:, 0].tolist()
                    ):  # already a column with this name
                        name = f"{name}_"  # dunno... dumb way to enforce uniqueness
                dt += [
                    (name, sample_types(obj[1]["DATA_TYPE"], obj[1]["BYTES"]))
                ]
    return np.dtype(dt)


def read_table(filename, label, pointer="TABLE"):  # ^TABLE
    file_area = get_file_area(label, pointer)[0]
    # TODO:
    # this is a placeholder.
    # it would be better to read FWF properly
    # and look for the correct delimiter.
    if file_area["INTERCHANGE_FORMAT"] == "ASCII":
        return pd.read_csv(
            filename, engine="python", sep=r"[\s|,]+", header=None
        )

    # otherwise treat it as binary.
    dt = parse_table_structure(label, pointer)
    return pd.DataFrame(
        np.fromfile(
            filename,
            dtype=dt,
            offset=data_start_byte(label, pointer),
            count=file_area["ROWS"],
        ).byteswap().newbyteorder()  # Pandas doesn't do non-native endian
    )


def null(*args):
    return None


# mapping between pointer names and functions intended to handle objects
# of that category
DEFAULT_POINTER_TO_FUNCTION_MAP = {
    "IMAGE": read_image,
    "IMAGE_HEADER": read_image_header,
    "FILE_NAME": read_file_name,
    "TABLE": read_table,
    "DESCRIPTION": read_description,
    "MEASUREMENT_TABLE": read_measurement_table,
    "ENGINEERING_TABLE": read_engineering_table,
    "L0_LINE_PREFIX_TABLE": read_CH1_M3_L0_prefix_table,
    "HISTOGRAM": read_histogram,
    "IMAGE_HISTOGRAM": read_histogram
}
# 'safe' immutable view of this dict
WORKING_POINTER_TO_FUNCTION_MAP = MappingProxyType(
    DEFAULT_POINTER_TO_FUNCTION_MAP)


def dispatched_read(target, label, pointer,
                    function_map=WORKING_POINTER_TO_FUNCTION_MAP):
    """
    find the appropriate reader function for the passed object / pointer
    and return its output.
    """
    # 'target' will generally be a filename or an integer representing a byte
    # offset within a file with an attached label.

    if isinstance(pointer, dict):
        object_name = pointer["object"][-1]
    else:
        object_name = pointer

    # defined special case?
    if object_name in function_map.keys():
        reader = function_map[object_name]
    # otherwise try generic readers, which may well handle cases in their
    # own right
    elif "IMAGE" in object_name:
        # weirdly named image pointer?
        reader = read_image
    elif "TABLE" in object_name:
        # weirdly named table pointer?
        reader = read_table
    # finally, just try to read it as text / bytes
    else:
        reader = read_document
    return reader(target, label, pointer)


# def read_any_file(filename):
class Data:
    def __init__(self, filename, lazy=False, suppress_warnings=False):

        # 'lazy' lazy-loads the data.
        # useful if you don't want to load in giant files at initialization
        # or if there is some problem with one or more of the input files.
        # look for PDS3 stuff
        setattr(self, "filename", filename)
        setattr(self, "LABEL", read_label(filename))
        setattr(self, "objects", find_pvl_objects(self.LABEL))
        setattr(
            self,
            "pointers",
            find_pointers(self.LABEL, path=os.path.split(filename)[0]),
        )
        if not suppress_warnings:
            self.warn_orphans()

        # Try PDS3 options
        if not lazy:
            self.load_all()

        # Sometimes images do not have explicit pointers, so just always try
        # to read an image out of the file no matter what.

        # TODO: I'm not actually sure how read_image is supposed to behave
        #  when passed a label without explicit pointers, so I'm currently
        #  treating this as a fallback case and using rasterio to try to
        #  open it. probably a more complex decision tree is required to
        #  look for info in the file and try to use struct, etc. -- Michael
        if not self.pointers:
            try:
                image = rasterio.open(filename).read()
                if image is not None:
                    setattr(self, "IMAGE", image)
            except (NameError, RasterioIOError):
                pass

        if (not self.pointers) and (not ("IMAGE" in dir(self))):
            if not suppress_warnings:
                print(
                    "Warning: PDS3 label parsed correctly, but does not "
                    "appear to contain references to any files and no "
                    "parsable files were automatically found. "
                )

    def __repr__(self):
        return str(
            "pdr.Data from "
            + self.filename
            + " with loaded objects "
            + str([obj for obj in self.loaded_objects])
        )

    def load_from_pointer(self, pointer):
        # attempt to load an object based on its pointer and the parsed
        # label. TODO: in the case of line prefixes etc., this isn't super
        #  performant, because multiple pointers point at the same file,
        #  requiring it to be parsed twice. probably not super important but
        #  worth considering. one special case to prevent this (for M3) is
        #  currently built in.
        if isinstance(pointer, str):
            match = [
                point for point in self.pointers if pointer in point["object"]
            ]
            if match:
                pointer = match[
                    0
                ]  # please, PDS3, do not have duplicated pointers
            else:
                raise KeyError("No pointer by that name.")

        obj = pointer["object"][-1]
        # ugly special case, sorry, i was out of memory, i'll make it better
        # later -- or maybe we need a whole special case dictionary
        if obj == "L0_LINE_PREFIX_TABLE":
            prefix, image = dispatched_read(pointer["target"], self.LABEL,
                                            pointer)
            setattr(self, obj, prefix)
            setattr(self, "L0_IMAGE", image)
            self.loaded_objects.append("L0_LINE_PREFIX_TABLE")
            self.loaded_objects.append("L0_IMAGE")
        elif obj == "L0_IMAGE":
            pass
        else:
            setattr(
                self, obj,
                dispatched_read(pointer["target"], self.LABEL, pointer)
            )
            if not (obj in self.loaded_objects):
                self.loaded_objects.append(pointer["object"][-1])

    def load_all(self):
        if self.pointers:
            for pointer in self.pointers:
                self.load_from_pointer(pointer)

    def warn_orphans(self):
        """
        print warnings about orphaned pointers and objects.
        """
        for obj in self.objects:
            if obj not in [pointer["object"][0] for pointer in self.pointers]:
                print(
                    "Warning: an object named "
                    + obj
                    + " is referenced in the label but no explicit pointer "
                    + "exists to an associated file. "
                )
        for pointer in self.pointers:
            if pointer["object"][0] not in self.objects:
                print(
                    "Warning: an pointer to an object named "
                    + pointer["object"][0]
                    + " is given in the label but no such object "
                    + "is actually found in the label. "
                )

    loaded_objects = []
