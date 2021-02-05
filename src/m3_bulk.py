"""
little ad-hoc fixes and support functions
for m3 bulk conversion processes
"""

import datetime as dt
import re
from types import MappingProxyType

import fs.path
import sh

from converter import PDSVersionConverter
from converter_utils import reloc, path_stem
from m3_conversion import interpret_m3_basename


def basenamer(string):
    return interpret_m3_basename(string)["basename"]


# what kind of files does each pds4 observational data product
# have, and what extensions do we expect each pds3 observational
# data product have?
# note that paths to newly-written versions are stored in
# attributes of the associated PDSVersionConverter instance.
L0_EXTS = (".LBL", ".HDR", ".IMG")
L1B_EXTS = (
    "L1B.LBL", "TIM.TAB", "OBS.HDR", "OBS.IMG", "LOC.HDR", "LOC.IMG",
    "RDN.HDR", "RDN.IMG"
)
L2_EXTS = ("L2.LBL", "SUP.HDR", "SUP.IMG", "RFL.HDR", "RFL.IMG")

PDS4_FILETYPES = MappingProxyType({
    'l0': ('pds4_label_file', 'clock_file', 'fits_image_file'),
    'l1b': ('pds4_label_file', 'loc_file', 'tim_file', 'rdn_file', 'obs_file'),
    'l2': ('pds4_label_file', 'sup_file', 'rfl_file')
})


def make_m3_triplet(group):
    df = group[1]
    # cutting the slash off the front, and the variably-long extension off
    # the end
    l0_stem = reloc(df, "lid", "_l0")["filepath"].iloc[0][1:-4]
    l1b_stem = reloc(df, "lid", "_l1b")["filepath"].iloc[0][1:-7]
    l2_stem = reloc(df, "lid", "_l2")["filepath"].iloc[0][1:-6]
    return {
        'l0': [l0_stem + ext for ext in L0_EXTS],
        'l1b': [l1b_stem + ext for ext in L1B_EXTS],
        'l2': [l2_stem + ext for ext in L2_EXTS]
    }


def m3_triplet_bundle_paths(group):
    return {
        'l0': path_stem(reloc(group[1], "lid", "_l0")["new_filepath"].iloc[0]),
        'l1b': path_stem(
            reloc(group[1], "lid", "_l1b")["new_filepath"].iloc[0]),
        'l2': path_stem(reloc(group[1], "lid", "_l2")["new_filepath"].iloc[0]),
    }


def crude_time_log(logfile: str, writer: PDSVersionConverter,
                   extra_time: str = "") -> None:
    with open(logfile, "a") as file:
        file.write(
            fs.path.split(writer.pds4_label_file)[1]
            + ","
            + dt.datetime.now().isoformat()
            + ","
            + extra_time
            + "\n"
        )


def make_m3_singlet(group):
    df = group[1]
    # cutting the slash off the front, and the variably-long extension off
    # the end
    l0_stem = reloc(df, "lid", "_l0")["filepath"].iloc[0][1:-4]
    return {
        'l0': [l0_stem + ext for ext in L0_EXTS],
    }


def m3_singlet_bundle_paths(group):
    return {
        'l0': path_stem(reloc(group[1], "lid", "_l0")["new_filepath"].iloc[0])
    }


def make_temp_filesystem(root, mb_size):
    with sh.contrib.sudo:
        sh.mount(
            "-t",
            "tmpfs",
            "-o",
            "size=" + str(mb_size) + "M",
            "tmpfs",
            root
        )


def fix_end_object_tags(pds3_label_file):
    """
    silly impure function that fixes END_OBJECT tags in some
    m3 target-mode labels (by making a new, fixed version of the label file)
    """
    with open(pds3_label_file) as file:
        label_string = file.read()
    temp_label_path = pds3_label_file + "_temp_fixed.LBL"
    with open(temp_label_path, 'w') as file:
        label_string = re.sub("L0_MAGE", "L0_IMAGE", label_string)
        label_string = re.sub("RDN_MAGE", "RDN_IMAGE", label_string)
        file.write(label_string)
    return temp_label_path
