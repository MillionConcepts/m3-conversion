"""
utility functions and PDR subclasses for converting PDS3 to PDS4 products.


"""

import re
import shutil
from functools import partial
from operator import contains, or_
from typing import List

import fs.path
from more_itertools import split_at, nth, chunked
from toolz import curry

from converter_utils import eqloc, name_root, are_in
from pdr import pdr

# ANSI FIGlet 'Electronic'
#  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄       ▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄            ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄
# ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░▌     ▐░░▌▐░░░░░░░░░░░▌▐░▌          ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌
#  ▀▀▀▀█░█▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀ ▐░▌░▌   ▐░▐░▌▐░█▀▀▀▀▀▀▀█░▌▐░▌          ▐░█▀▀▀▀▀▀▀█░▌ ▀▀▀▀█░█▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀
#      ▐░▌     ▐░▌          ▐░▌▐░▌ ▐░▌▐░▌▐░▌       ▐░▌▐░▌          ▐░▌       ▐░▌     ▐░▌     ▐░▌
#      ▐░▌     ▐░█▄▄▄▄▄▄▄▄▄ ▐░▌ ▐░▐░▌ ▐░▌▐░█▄▄▄▄▄▄▄█░▌▐░▌          ▐░█▄▄▄▄▄▄▄█░▌     ▐░▌     ▐░█▄▄▄▄▄▄▄▄▄
#      ▐░▌     ▐░░░░░░░░░░░▌▐░▌  ▐░▌  ▐░▌▐░░░░░░░░░░░▌▐░▌          ▐░░░░░░░░░░░▌     ▐░▌     ▐░░░░░░░░░░░▌
#      ▐░▌     ▐░█▀▀▀▀▀▀▀▀▀ ▐░▌   ▀   ▐░▌▐░█▀▀▀▀▀▀▀▀▀ ▐░▌          ▐░█▀▀▀▀▀▀▀█░▌     ▐░▌     ▐░█▀▀▀▀▀▀▀▀▀
#      ▐░▌     ▐░▌          ▐░▌       ▐░▌▐░▌          ▐░▌          ▐░▌       ▐░▌     ▐░▌     ▐░▌
#      ▐░▌     ▐░█▄▄▄▄▄▄▄▄▄ ▐░▌       ▐░▌▐░▌          ▐░█▄▄▄▄▄▄▄▄▄ ▐░▌       ▐░▌     ▐░▌     ▐░█▄▄▄▄▄▄▄▄▄
#      ▐░▌     ▐░░░░░░░░░░░▌▐░▌       ▐░▌▐░▌          ▐░░░░░░░░░░░▌▐░▌       ▐░▌     ▐░▌     ▐░░░░░░░░░░░▌
#       ▀       ▀▀▀▀▀▀▀▀▀▀▀  ▀         ▀  ▀            ▀▀▀▀▀▀▀▀▀▀▀  ▀         ▀       ▀       ▀▀▀▀▀▀▀▀▀▀▀
"""
template processing utilities.
caution:
these are not general-purpose xml-parsing functions!
they are simple, expressive, and fast, but not powerful.
exercise great care using them to manipulate xml that 
is not being generated under your strict control.
"""

LID_PATTERN = re.compile(r'urn.*?(?=</logical)')
LID_END_PATTERN = re.compile(r'((\w)|(\d)|[-._])+(?=</logical)')
FN_PATTERN = re.compile(r'(?<=file_name>).*?(?=</file_name)')


def template_tags(template_fn):
    """return list of tags from a template file"""
    with open(template_fn) as template:
        tags = re.findall(r'{.*?}', template.read())
    return set(tags)


def inside_the_tag(xml_line: str) -> map:
    """
    get values from XML.
    caution:
    this is not a 'real' general-purpose xml-parsing function!
    exercise great care using it to parse xml that is not being
    generated under your strict control.
    """
    xml_tag = r"<.*?>"
    splits = re.split(
        xml_tag,
        xml_line
    )
    return map(partial(nth, n=1), (chunked(splits, 3)))


def manipulate_xml_tag(label, tag, manipulator):
    """
    constrain all values in XML wrapped in a particular tag or tag pattern.
    caution:
    this is not a 'real' general-purpose xml-parsing function!
    exercise great care using it to parse xml that is not being
    generated under your strict control.
    """
    lines = label.splitlines()
    output_lines = []
    for line in lines:
        if tag in line:
            value = next(inside_the_tag(line))
            output_lines.append(manipulator(line, value))
        else:
            output_lines.append(line)
    return "\n".join(output_lines)


def round_xml_tag(label, tag, digits):
    def rounder(line, value):
        return line.replace(
            value,
            str(format(float(value), '.' + str(digits)))
        )
    return manipulate_xml_tag(label, tag, rounder)


def constrain_xml_tag(label, tag, minimum, maximum, threshold):
    def constrainer(line, value):
        if (float(value) >= minimum) and (float(value) <= maximum):
            return line
        elif (float(value) - minimum) < threshold:
            return line.replace(
                value,
                str(minimum)
            )
        elif (float(value) - maximum) < threshold:
            return line.replace(
                value,
                str(maximum)
            )
        else:
            raise ValueError(tag + " is out of bounds.")
    return manipulate_xml_tag(label, tag, constrainer)


def get_element_block(
    xml_string: str,
    first_name: str,
    second_name: str = None,
    include_initial: bool = True,
    include_final: bool = True
) -> str:
    """
    warning: use great caution if attempting to apply this function,
    or anything like it, to tags that that may appear more than once in the
    label. this _general type of_ approach to XML parsing works reliably
    only in the special case where tag names (or sequences of tag names,
    etc.) are unique (or their number of occurrences are otherwise precisely known)
    """
    if second_name is None:
        element_names = [first_name]
    else:
        element_names = [first_name, second_name]
    split = tuple(split_at(
            xml_string.splitlines(),
            are_in(element_names, or_),
            keep_separator=True
        ))
    chunk = split[2]
    if include_initial:
        chunk = split[1] + chunk
    if include_final:
        chunk = chunk + split[3]
    return "\n".join(chunk)


def enforce_name_match(label, root, file=None):
    """
    crude error checking function that enforces parity between file root
    names, logical_identifier tags in labels, and file_name tags in labels.
    not appropriate for products with multiple files.
    """
    fn_tag = re.search(FN_PATTERN, label).group(0)
    lid_end_tag = re.search(LID_END_PATTERN, label).group(0)
    # enforce match between these tags and putative filename root
    try:
        assert name_root(fn_tag) == lid_end_tag
    except AssertionError:
        raise ValueError(
            "real product filename mismatch with LID: "
            + "\n" + name_root(fn_tag) + " does not match "
            + lid_end_tag + " in " + root
        )
    try:
        assert lid_end_tag == root
    except AssertionError:
        raise ValueError(
            "LID mismatch with nominal product filename root: "
            + "\n" + lid_end_tag + " does not match " + root
        )
    if file is not None:
        try:
            assert fn_tag == file
        except AssertionError:
            raise ValueError(
                "Mismatch between XML-tagged filename and written filename: "
                + "\n" + fn_tag + " does not match " + file
            )


def process_deletions(
        lines: List[str],
        deletions: List[str]
) -> List[str]:
    output_lines = []
    delete_flag = False
    deletion_target = None
    for line in lines:
        # delete template comments
        if '<!--' in line:
            continue
        if delete_flag:
            # this is our 'skip all these lines, deletion on' state
            if '{delete:' not in line:
                continue
            if deletion_target == re.search(
                    r'{delete:(\w.*?):', line
            ).group(1):
                # i.e., does this tag match the opening deletion tag?
                delete_flag = False
                continue
            continue
        if '{delete:' in line:
            if ':stop}' in line:
                # unmatched stop tag -- delete it and move on.
                continue
            # is this a tag we're deleting? delete the deletion command itself
            # in any case.
            deletion_target = re.search(r'{delete:(\w.*?):', line).group(1)
            if any([
                contains(deletion, deletion_target)
                for deletion in deletions
            ]):
                delete_flag = True
                continue
            continue
        else:
            output_lines.append(line)
    return output_lines


#   ▄▄▄▄▄▄▄▄▄▄▄  ▄            ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄
#  ▐░░░░░░░░░░░▌▐░▌          ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌
#  ▐░█▀▀▀▀▀▀▀▀▀ ▐░▌          ▐░█▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀
#  ▐░▌          ▐░▌          ▐░▌       ▐░▌▐░▌          ▐░▌          ▐░▌          ▐░▌
#  ▐░▌          ▐░▌          ▐░█▄▄▄▄▄▄▄█░▌▐░█▄▄▄▄▄▄▄▄▄ ▐░█▄▄▄▄▄▄▄▄▄ ▐░█▄▄▄▄▄▄▄▄▄ ▐░█▄▄▄▄▄▄▄▄▄
#  ▐░▌          ▐░▌          ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌
#  ▐░▌          ▐░▌          ▐░█▀▀▀▀▀▀▀█░▌ ▀▀▀▀▀▀▀▀▀█░▌ ▀▀▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀█░▌
#  ▐░▌          ▐░▌          ▐░▌       ▐░▌          ▐░▌          ▐░▌▐░▌                    ▐░▌
#  ▐░█▄▄▄▄▄▄▄▄▄ ▐░█▄▄▄▄▄▄▄▄▄ ▐░▌       ▐░▌ ▄▄▄▄▄▄▄▄▄█░▌ ▄▄▄▄▄▄▄▄▄█░▌▐░█▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄█░▌
#  ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░▌       ▐░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌
#   ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀         ▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀

"""
parent classes for product writers specified in submodules such as clem_conversion
"""


def _convert_label(
        converter,
        output_directory,
        write_label_file=True,
        label_name=None,
        verbose=True
):
    """
    create PDS4 label using xml templates.
    (string containing output directory -> True)

    this is primarily intended to be used as a method
    in PDSVersionConverter and PDS4Writer.

    impure: places new label in self.PDS4_LABEL, and if dry_run is
    set to False, writes it to output_directory.
    looks for external template at the path given by self.template .
    requires: a tag mapping created by self.generate_tag_mapping(),
    which will often be generated at least partly from a PDS3 label in
    self.LABEL. maybe add a naive version later?
    """
    if label_name is None:
        converter.pds4_label_file = (
            fs.path.join(
                output_directory,
                name_root(converter.filename).lower() + ".xml"
            )
        )
    else:
        converter.pds4_label_file = output_directory + label_name + ".xml"
    converter.tag_mapping = converter.generate_tag_mapping()

    with open(converter.template, "r") as template_file:
        template = template_file.readlines()

    deletions = [tag for tag in converter.tag_mapping if '{delete:' in tag]
    template = process_deletions(template, deletions)

    output_lines = []
    for line in template:
        for key in converter.tag_mapping.keys():
            if key in line:
                line = line.replace(key, str(converter.tag_mapping[key]))
        if not re.match(r"\s+\n", line):
            output_lines.append(line)
    converter.PDS4_LABEL = output_lines
    if write_label_file:
        if verbose:
            print("Writing PDS4 label to " + converter.pds4_label_file)
        with open(converter.pds4_label_file, "w") as xml_file:
            xml_file.writelines(converter.PDS4_LABEL)
    return True


class PDSVersionConverter(pdr.Data):
    def __init__(self, filename, *, label_only=False, **pdr_kwargs):
        # default values for attributes hopefully set by PDR
        self.LABEL = {}
        self.pointers = []
        if not label_only:
            super().__init__(filename, **pdr_kwargs)
        else:
            # this might be a messy option, but implementing it now for
            # convenience. the label_only flag allows this class to be used
            # as _just_ a label reader / converter
            setattr(self, "filename", filename)
            # Try PDS3 options
            setattr(self, "LABEL", pdr.read_label(filename))
            setattr(
                self,
                "pointers",
                [k for k in self.LABEL.keys() if k[0] == "^"],
            )
            _ = [
                setattr(
                    self,
                    pointer[1:] if pointer.startswith("^") else pointer,
                    pdr.WORKING_POINTER_TO_FUNCTION_MAP[pointer](filename,
                                                                 self.LABEL),
                )
                for pointer in self.pointers
            ]
        setattr(self, "convert_label", curry(_convert_label)(self))


class PDS4Writer:
    """sad version of PDSVersionConverter. class for generating PDS4
    products from files without PDS3 labels. """

    def __init__(self, filename):
        setattr(self, "filename", filename)
        setattr(self, "write_label", curry(_convert_label)(self))


def re_search(filename, pattern):
    with open(filename) as file:
        return re.search(pattern, file.read()).group(0)


def place_label(
        product,
        label_df,
        product_file,
        base_dir
):
    """
    simple label-and-file pairing and moving function, with error checking,
    for "one-off", untemplated labels that correspond to single files.
    basically just shutil.copy wrapped in a couple of semantic sanity checks.
    """
    # enforce match between putative filename root and label filename
    try:
        label_file = eqloc(
            label_df, "filename", product.root
        )["local_path"].values[0]
    except KeyError:
        raise KeyError("Label for " + product.root + " not found in index.")

    # check stated filename and product id
    with open(label_file) as file:
        label = file.read()
    enforce_name_match(label, product.root)

    # and then copy label to correct place
    shutil.copy(label_file, base_dir + product.newpath)
    # and finally copy source file to filepath listed in label
    if product_file:
        fn_tag = re.search(FN_PATTERN, label).group(0)
        shutil.copy(product_file, base_dir + product.newpath + "/" + fn_tag)
    return {
        'product_id': re_search(label_file, LID_PATTERN),
        'label': base_dir + product.newpath + "/" + product.root + ".xml"
    }
