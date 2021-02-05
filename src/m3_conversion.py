"""
specialized utilities and PDSVersionConverter / PDS4Writer subclasses for
converting m3 products.
"""
from ast import literal_eval
import datetime as dt
import os
import re
import shutil

import numpy as np
import pandas as pd
import rasterio
from toolz import merge

from converter import PDSVersionConverter, PDS4Writer, template_tags
from converter_utils import fitsify, null_bytes_to_na, get_from_and_apply, \
    reloc, eqloc

# utilities

# what m3 'base names' look like
M3_BASENAME_PATTERN = re.compile(
    r"M3([GT])(20\d\d)(\d\d)(\d\d)T(\d\d)(\d\d)(\d\d).*?(?=[_.])",
    flags=re.I
)


def interpret_m3_basename(path):
    """
    extracts m3 basename, mode, and iso-formatted time from a filename.
    """
    filename = re.search(M3_BASENAME_PATTERN, path)
    if filename is None:
        raise ValueError("No M3 file base name found in this string.")
    return {
        "mode": "global" if filename.group(1) == "G" else "target",
        "time": dt.datetime(
            int(filename.group(2)),
            int(filename.group(3)),
            int(filename.group(4)),
            int(filename.group(5)),
            int(filename.group(6)),
        ).isoformat()
        + "Z",
        "basename": filename.group(0)[:18],
        "filename": filename.group(0),
    }


def m3_generic_tags(label):
    """
    get values for tags found in all m3 observational products
    """
    get_pds3 = get_from_and_apply(label)
    return {
        "{product_id}": get_pds3("PRODUCT_ID"),
        "{detector_temperature}": get_pds3("DETECTOR_TEMPERATURE"),
        "{start_time}": get_pds3("START_TIME", func=dt.datetime.isoformat),
        "{stop_time}": get_pds3("STOP_TIME", func=dt.datetime.isoformat),
        "{spacecraft_clock_start}": get_pds3("SPACECRAFT_CLOCK_START_COUNT"),
        "{spacecraft_clock_stop}": get_pds3("SPACECRAFT_CLOCK_STOP_COUNT"),
        "{orbit_number}": get_pds3("ORBIT_NUMBER"),
        "{instrument_mode_id}": get_pds3("INSTRUMENT_MODE_ID").capitalize(),
        "{swath_length}": get_pds3("CH1:SWATH_LENGTH", "value"),
        "{swath_width}": get_pds3("CH1:SWATH_WIDTH", "value"),
        "{product_creation_time}": get_pds3(
            "PRODUCT_CREATION_TIME", func=dt.datetime.isoformat
        ),
        "{software_name}": get_pds3("SOFTWARE_NAME"),
        "{software_version}": get_pds3("SOFTWARE_VERSION_ID"),
    }


def m3_orientation_tags(label):
    """
    construct template tags for m3 orientation model attributes
    from PDS3 labels. used in L1B and L2 products
    """
    get_pds3 = get_from_and_apply(label)

    # these attributes should always be present
    tag_dictionary = {
        "{spacecraft_yaw_direction}": get_pds3(
            "CH1:SPACECRAFT_YAW_DIRECTION"
        ).capitalize(),
        "{orbit_limb_direction}": get_pds3(
            "CH1:ORBIT_LIMB_DIRECTION").capitalize(),
        "{solar_distance}": get_pds3("SOLAR_DISTANCE",
                                     func=lambda x: str(x.value)),
    }
    # initialize blank values for all attitude-dependent tags
    for tag in [
        "{orientation_epoch_time}",
        "{spacecraft_rotation_rate}",
        "{initial_spacecraft_orientation_tag}",
        "{initial_roll_tag}",
        "{initial_pitch_tag}",
        "{initial_yaw_tag}",
        "{close_initial_spacecraft_orientation_tag}",
        "{spacecraft_orientation_rates_tag}",
        "{roll_rate_tag}",
        "{pitch_rate_tag}",
        "{yaw_rate_tag}",
        "{close_spacecraft_orientation_rates_tag}",
        "{spacecraft_orientation_axis_vector_tag}",
        "{x_unit_tag}",
        "{y_unit_tag}",
        "{z_unit_tag}",
        "{close_spacecraft_orientation_axis_vector_tag}",
        "{spacecraft_orientation_tag}",
        "{roll_tag}",
        "{pitch_tag}",
        "{yaw_tag}",
        "{close_spacecraft_orientation_tag}",
    ]:
        tag_dictionary[tag] = ""

    # should always be present

    spacecraft_orientation = get_pds3("SPACECRAFT_ORIENTATION")
    # this variable is basically the entirety of model 1
    if "N/A" not in spacecraft_orientation:
        # populate model 1
        spacecraft_orientation = literal_eval(spacecraft_orientation)
        tag_dictionary[
            "{spacecraft_orientation_tag}"
        ] = "<chan1:Spacecraft_Orientation>"
        tag_dictionary["{roll_tag}"] = (
                """<chan1:roll unit="deg">"""
                + str(spacecraft_orientation[0])
                + "</chan1:roll>"
        )
        tag_dictionary["{pitch_tag}"] = (
                """<chan1:pitch unit="deg">"""
                + str(spacecraft_orientation[1])
                + "</chan1:pitch>"
        )
        tag_dictionary["{yaw_tag}"] = (
                """<chan1:yaw unit="deg">"""
                + str(spacecraft_orientation[2])
                + "</chan1:yaw>"
        )
        tag_dictionary[
            "{close_spacecraft_orientation_tag}"
        ] = "</chan1:Spacecraft_Orientation>"

    initial_orientation = get_pds3("CH1:INITIAL_SC_ORIENTATION")
    if "N/A" not in initial_orientation:
        initial_orientation = literal_eval(initial_orientation)
        tag_dictionary[
            "{initial_spacecraft_orientation_tag}"
        ] = "<chan1:Initial_Spacecraft_Orientation>"
        tag_dictionary["{initial_roll_tag}"] = (
                """<chan1:roll unit="deg">"""
                + str(initial_orientation[0])
                + "</chan1:roll>"
        )
        tag_dictionary["{initial_pitch_tag}"] = (
                """<chan1:pitch unit="deg">"""
                + str(initial_orientation[1])
                + "</chan1:pitch>"
        )
        tag_dictionary["{initial_yaw_tag}"] = (
                """<chan1:yaw unit="deg">""" + str(
                    initial_orientation[2]) + "</chan1:yaw>"
                )
        tag_dictionary[
            "{close_initial_spacecraft_orientation_tag}"
        ] = "</chan1:Initial_Spacecraft_Orientation>"

    orientation_epoch_time = get_pds3("CH1:SC_ORIENTATION_EPOCH_TDB_TIME")
    if "N/A" not in orientation_epoch_time:
        tag_dictionary["{orientation_epoch_time}"] = (
                """<chan1:orientation_epoch_time unit="s">"""
                + orientation_epoch_time
                + "</chan1:orientation_epoch_time>"
        )

    rotation_axis_vector = get_pds3("CH1:SC_ROTATION_AXIS_VECTOR")
    if "N/A" not in rotation_axis_vector:
        # get model 3 data. ok throwing errors here if it's not all present,
        # means we need to check this process.
        rotation_axis_vector = literal_eval(rotation_axis_vector)
        tag_dictionary["{spacecraft_rotation_rate}"] = (
                """<chan1:spacecraft_rotation_rate unit="deg/s">"""
                + get_pds3("CH1:SC_ROTATION_RATE")
                + "</chan1:spacecraft_rotation_rate>"
        )
        tag_dictionary[
            "{spacecraft_orientation_axis_vector_tag}"
        ] = "<chan1:Spacecraft_Orientation_Axis_Vector>"
        tag_dictionary["{x_unit_tag}"] = (
            "<chan1:x_unit>" + str(
                rotation_axis_vector[0]) + "</chan1:x_unit>"
            )
        tag_dictionary["{y_unit_tag}"] = (
            "<chan1:y_unit>" + str(
                rotation_axis_vector[1]) + "</chan1:y_unit>"
            )
        tag_dictionary["{z_unit_tag}"] = (
            "<chan1:z_unit>" + str(
                rotation_axis_vector[2]) + "</chan1:z_unit>"
            )
        tag_dictionary[
            "{close_spacecraft_orientation_axis_vector_tag}"
        ] = "</chan1:Spacecraft_Orientation_Axis_Vector>"

    orientation_rate = get_pds3("CH1:SC_ORIENTATION_RATE")
    if "N/A" not in orientation_rate:
        # get model 2 data. ok throwing errors here if it's not all present,
        # means we need to check this process.
        orientation_rate = literal_eval(orientation_rate)
        tag_dictionary[
            "{spacecraft_orientation_rates_tag}"
        ] = "<chan1:Spacecraft_Orientation_Rates>"
        tag_dictionary["{roll_rate_tag}"] = (
                """<chan1:roll_rate unit="deg/s">"""
                + str(orientation_rate[0])
                + "</chan1:roll_rate>"
        )
        tag_dictionary["{pitch_rate_tag}"] = (
                """<chan1:pitch_rate unit="deg/s">"""
                + str(orientation_rate[1])
                + "</chan1:pitch_rate>"
        )
        tag_dictionary["{yaw_rate_tag}"] = (
                """<chan1:yaw_rate unit="deg/s">"""
                + str(orientation_rate[2])
                + "</chan1:yaw_rate>"
        )
        tag_dictionary[
            "{close_spacecraft_orientation_rates_tag}"
        ] = "</chan1:Spacecraft_Orientation_Rates>"

    return tag_dictionary


def m3_latlon_tags(writer, product_index="./directories/m3/m3_index.csv"):
    """
    PDSVersionConverter -> dict
    reads lat/lon bounds directly out of an L1B product's LOC file bounds,
    or out of an index for L0 and L2 products
    """
    if "L1B" in writer.filename:
        try:
            return {
                "{minimum_latitude}": np.min(writer.LOC_IMAGE[1]),
                "{maximum_latitude}": np.max(writer.LOC_IMAGE[1]),
                "{minimum_longitude}": np.min(writer.LOC_IMAGE[0]),
                "{maximum_longitude}": np.max(writer.LOC_IMAGE[0]),
            }
        except (IndexError, AttributeError):
            print(
                "LOC image not loaded. Using placeholder 0"
                + " value for lat/lon in label."
            )
            return {
                "{minimum_latitude}": 0,
                "{maximum_latitude}": 0,
                "{minimum_longitude}": 0,
                "{maximum_longitude}": 0,
            }
    else:
        try:
            basename = interpret_m3_basename(writer.filename)[
                "basename"].lower()
            table = pd.read_csv(product_index)
            product_line = eqloc(table, "basename", basename)
            return {
                "{minimum_latitude}": product_line.minimum_latitude.iloc[0],
                "{maximum_latitude}": product_line.maximum_latitude.iloc[0],
                "{minimum_longitude}": product_line.minimum_longitude.iloc[0],
                "{maximum_longitude}": product_line.maximum_longitude.iloc[0],
            }
        except (FileNotFoundError, IndexError, KeyError):
            print(
                "Product not found in index, or index not found. Perhaps the "
                "corresponding L1B product should be converted first. Using "
                "placeholder 0 value for lat/lon in label."
            )
            return {
                "{minimum_latitude}": 0,
                "{maximum_latitude}": 0,
                "{minimum_longitude}": 0,
                "{maximum_longitude}": 0,
            }


# conversion classes
# some of these are repetitive. they are intended to make it easy
# to add additional behavior during liens or reprocessing efforts.
class M3L0Converter(PDSVersionConverter):
    """
    implements business logic for M3 L0-specific PDS version conversion
    """

    def __init__(
            self, filename, *, template="./labels/m3/l0_template.xml",
            clean=False, **pdr_kwargs
    ):
        # default values for known attributes populated later
        self.LABEL = None
        self.L0_LINE_PREFIX_TABLE = None
        self.L0_IMAGE = np.array([])
        self.filename = None
        self.fits_image_file = None
        self.clock_file = None

        super().__init__(filename, **pdr_kwargs)
        # stymie numpy's enthusiasm for 64-bit integers and roll into an
        # HDUList
        self.FITS_IMAGE = fitsify(self.L0_IMAGE.astype("int16"))
        self.PREFIX_DATAFRAME = pd.DataFrame(self.L0_LINE_PREFIX_TABLE)
        # replace missing-byte strings (which are present in most of the files,
        # and _supposed_ to be present in all) with 'n/a' and put that info
        # at the end (so that order of most of the fields corresponds to
        # 1-indexed
        # byte order rather than 2-indexed)
        self.PREFIX_DATAFRAME[23] = self.PREFIX_DATAFRAME[0].apply(
            null_bytes_to_na)
        self.PREFIX_DATAFRAME.drop(0, axis=1, inplace=True)
        if clean:
            del self.L0_IMAGE
        self.template = template
        self.pds4_root = (
                interpret_m3_basename(self.filename)[
                    "basename"].lower() + "_l0"
        )

    def generate_tag_mapping(self):
        """
        make a dictionary of mappings to tags in PDS4 label template.
        no arguments, looks for parameters in self.LABEL.
        """
        get_pds3 = get_from_and_apply(self.LABEL)
        m3_info = interpret_m3_basename(self.filename)
        try:
            clock_file_size = str(os.stat(self.clock_file).st_size)
            fits_file_size = str(os.stat(self.fits_image_file).st_size)
        except (AttributeError, TypeError, FileNotFoundError):
            print(
                "Converted prefix table and/or FITS image files have not "
                + "been written yet or were not found. Using placeholder "
                + "9999 value for file sizes in label."
            )
            clock_file_size = "9999"
            fits_file_size = "9999"

        l0_dictionary = {
            "{basename_lower}": m3_info["basename"].lower(),
            "{line_samples}": get_pds3("L0_FILE", "L0_IMAGE", "LINE_SAMPLES"),
            # in many (perhaps all) of the target-mode L0 PDS3 labels,
            # the line prefix tables are incorrectly specified as having
            # many more rows than they do, so that field can't be used to
            # generate new labels.
            "{rows}": get_pds3("L0_FILE", "L0_IMAGE", "LINES"),
            "{bands}": get_pds3("L0_FILE", "L0_IMAGE", "BANDS"),
            "{file_records}": get_pds3("L0_FILE", "FILE_RECORDS"),
            "{record_bytes}": get_pds3("L0_FILE", "RECORD_BYTES"),
            "{clock_file_size}": clock_file_size,
            "{fits_file_size}": fits_file_size,
        }

        generic_dictionary = m3_generic_tags(self.LABEL)
        if '{minimum_longitude}' in template_tags(self.template):
            # i.e., if it's not a 'lonely' EDR product with no reduced 
            # friends in the archive 
            latlon_dictionary = m3_latlon_tags(self)
        else:
            latlon_dictionary = {}

        return merge(l0_dictionary, generic_dictionary, latlon_dictionary)

    def write_pds4(
            self,
            output_directory,
            write_product_files=True,
            write_label_file=True,
            clean=False
    ):
        """
        output file objects and label for a PDS4 product corresponding to
        this object.
        (string containing output directory -> None)
        """
        print("Converting " + self.filename + " to PDS4.")
        self.fits_image_file = output_directory + self.pds4_root + ".fits"
        self.clock_file = output_directory + self.pds4_root + "_clock_table.csv"
        if write_product_files:
            self.FITS_IMAGE.writeto(self.fits_image_file, overwrite=True)
            self.PREFIX_DATAFRAME.to_csv(
                self.clock_file,
                index=False,
                header=False,
                # PDS4 DSV records must terminate with CRLF! therefore only
                # Windows machines will produce compliant output by default.
                # the following argument corrects this.
                line_terminator="\r\n",
            )
            if clean:
                del self.FITS_IMAGE
                del self.PREFIX_DATAFRAME

        self.convert_label(
            output_directory, write_label_file, label_name=self.pds4_root
        )


class M3L1BConverter(PDSVersionConverter):
    """
    implements business logic for M3 L1B-specific PDS version conversion
    """

    def __init__(
            self, filename, *, template="./labels/m3/l1b_template.xml",
            clean=False, **pdr_kwargs
    ):
        # default values for known attributes populated later
        self.OBS_IMAGE = np.array([])
        self.RDN_IMAGE = np.array([])
        self.LOC_IMAGE = np.array([])
        self.UTC_TIME_TABLE = None
        self.filename = None
        self.LABEL = None
        self.rdn_file = None
        self.loc_file = None
        self.obs_file = None
        self.tim_file = None

        # read the label with PDR
        super().__init__(filename, **pdr_kwargs)

        # roll images into HDULists of appropriate types
        self.fits_loc_image = fitsify(self.LOC_IMAGE.astype("float64"))
        self.fits_rdn_image = fitsify(self.RDN_IMAGE.astype("float32"))
        self.fits_obs_image = fitsify(self.OBS_IMAGE.astype("float32"))
        if clean:
            # LOC_IMAGE doesn't get deleted here because it's used in tag
            # mapping.
            # we may change that later.
            del self.RDN_IMAGE
            del self.OBS_IMAGE
        self.template = template
        self.pds4_root = (
                interpret_m3_basename(self.filename)[
                    "basename"].lower() + "_l1b"
        )

    def generate_tag_mapping(self):
        """
        make a dictionary of mappings to tags in PDS4 label template.
        no arguments, looks for parameters in self.LABEL.
        """
        get_pds3 = get_from_and_apply(self.LABEL)
        m3_info = interpret_m3_basename(self.filename)
        try:
            obs_file_size = str(os.stat(self.obs_file).st_size)
            loc_file_size = str(os.stat(self.loc_file).st_size)
            rdn_file_size = str(os.stat(self.rdn_file).st_size)
        except (AttributeError, FileNotFoundError):
            print(
                "Converted prefix table and/or FITS image files have not "
                + "been written yet or were not found. Using placeholder "
                + "9999 value for file sizes in label."
            )
            obs_file_size = "9999"
            loc_file_size = "9999"
            rdn_file_size = "9999"
        # note that the LOC, RDN, and OBS files all have the same number
        # of lines and samples.
        l1b_dictionary = {
            "{basename_lower}": m3_info["basename"].lower(),
            "{lines}": get_pds3("RDN_FILE", "RDN_IMAGE", "LINES"),
            "{samples}": get_pds3("RDN_FILE", "RDN_IMAGE", "LINE_SAMPLES"),
            "{rdn_bands}": get_pds3("RDN_FILE", "RDN_IMAGE", "BANDS"),
            "{rdn_file_size}": rdn_file_size,
            "{loc_file_size}": loc_file_size,
            "{obs_file_size}": obs_file_size,
            "{rad_gain_file}": get_pds3("CH1:RAD_GAIN_FACTOR_FILE_NAME")[
                               :-4].lower(),
            "{spectral_calibration_file}": get_pds3(
                "CH1:SPECTRAL_CALIBRATION_FILE_NAME"
            )[:-4].lower(),
        }
        generic_dictionary = m3_generic_tags(self.LABEL)
        orientation_dictionary = m3_orientation_tags(self.LABEL)
        latlon_dictionary = m3_latlon_tags(self)

        return merge(
            l1b_dictionary,
            latlon_dictionary,
            generic_dictionary,
            orientation_dictionary,
        )

    def write_pds4(
            self,
            output_directory,
            write_product_files=True,
            write_label_file=True,
            index_file="./directories/m3/m3_index.csv",
            clean=False
    ):
        """
        output file objects and label for a PDS4 product corresponding to
        this object.
        (string containing output directory -> None)
        """
        print("Converting " + self.filename + " to PDS4.")

        self.rdn_file = output_directory + self.pds4_root + "_rdn.fits"
        self.loc_file = output_directory + self.pds4_root + "_loc.fits"
        self.obs_file = output_directory + self.pds4_root + "_obs.fits"
        self.tim_file = output_directory + self.pds4_root + "_tim.tab"
        if write_product_files:
            self.fits_loc_image.writeto(self.loc_file, overwrite=True)
            self.fits_rdn_image.writeto(self.rdn_file, overwrite=True)
            self.fits_obs_image.writeto(self.obs_file, overwrite=True)
            self.UTC_TIME_TABLE[1] = self.UTC_TIME_TABLE[1] + "Z"
            self.UTC_TIME_TABLE.to_csv(
                self.tim_file,
                index=False,
                header=False,
                # PDS4 DSV records must terminate with CRLF! therefore only
                # Windows machines will produce compliant output by default.
                # the following argument corrects this.
                line_terminator="\r\n",
            )

        self.convert_label(
            output_directory, write_label_file, label_name=self.pds4_root
        )

        if clean:
            del self.fits_loc_image
            del self.fits_rdn_image
            del self.fits_obs_image
            # deleting these two here because they are actually used
            # in these writing functions
            del self.UTC_TIME_TABLE
            del self.LOC_IMAGE

        if index_file is not None:
            basename = interpret_m3_basename(self.filename)["basename"].lower()
            lat_series = pd.Series(
                {
                    "basename": basename,
                    "minimum_latitude": self.tag_mapping["{minimum_latitude}"],
                    "maximum_latitude": self.tag_mapping["{maximum_latitude}"],
                    "minimum_longitude": self.tag_mapping[
                        "{minimum_longitude}"],
                    "maximum_longitude": self.tag_mapping[
                        "{maximum_longitude}"],
                    "start_time": self.tag_mapping["{start_time}"],
                    "stop_time": self.tag_mapping["{stop_time}"],
                }
            )

            try:
                index = pd.read_csv(index_file)
                if len(reloc(index, "basename", basename)) > 0:
                    index.drop(reloc(index, "basename", basename).index,
                               inplace=True)
                index = index.append(lat_series, ignore_index=True)
                index.to_csv(index_file, index=False)
            except FileNotFoundError:
                pd.DataFrame(lat_series).T.to_csv(
                    index_file,
                    index=False
                )


class M3L2Converter(PDSVersionConverter):
    """
    implements business logic for M3 L1B-specific PDS version conversion
    """

    def __init__(
            self, filename, *, template="./labels/m3/l2_template.xml",
            clean=False, **pdr_kwargs
    ):
        # default values for known attributes populated later
        self.RFL_IMAGE = np.array([])
        self.SUPPL_IMAGE = np.array([])
        self.filename = None
        self.LABEL = None
        self.rfl_file = None
        self.sup_file = None

        # read the label with PDR
        super().__init__(filename, **pdr_kwargs)

        # roll images into HDULists of appropriate types
        self.fits_rfl_image = fitsify(self.RFL_IMAGE.astype("float32"))
        self.fits_sup_image = fitsify(self.SUPPL_IMAGE.astype("float32"))
        if clean:
            del self.RFL_IMAGE
            del self.SUPPL_IMAGE
        self.template = template
        self.pds4_root = (
                interpret_m3_basename(self.filename)[
                    "basename"].lower() + "_l2"
        )

    def generate_tag_mapping(self):
        """
        make a dictionary of mappings to tags in PDS4 label template.
        no arguments, looks for parameters in self.LABEL.
        """
        get_pds3 = get_from_and_apply(self.LABEL)
        m3_info = interpret_m3_basename(self.filename)
        try:
            rfl_file_size = str(os.stat(self.sup_file).st_size)
            sup_file_size = str(os.stat(self.sup_file).st_size)
        except (AttributeError, FileNotFoundError):
            print(
                "Converted FITS image files have not "
                + "been written yet or were not found. Using placeholder "
                + "9999 value for file sizes in label."
            )
            rfl_file_size = "9999"
            sup_file_size = "9999"

        # note that the RFL and SUP files have the same number
        # of lines and samples.
        l2_dictionary = {
            "{basename_lower}": m3_info["basename"].lower(),
            "{lines}": get_pds3("RFL_FILE", "RFL_IMAGE", "LINES"),
            "{samples}": get_pds3("RFL_FILE", "RFL_IMAGE", "LINE_SAMPLES"),
            "{rfl_bands}": get_pds3("RFL_FILE", "RFL_IMAGE", "BANDS"),
            "{rfl_file_size}": rfl_file_size,
            "{sup_file_size}": sup_file_size,
            "{rad_gain_file}": get_pds3("CH1:RAD_GAIN_FACTOR_FILE_NAME")[
                               :-4].lower(),
            "{spectral_calibration_file}": get_pds3(
                "CH1:SPECTRAL_CALIBRATION_FILE_NAME"
            )[:-4].lower(),
            "{stat_pol}": get_pds3("CH1:STATISTICAL_POLISHER_FILE_NAME")[
                          :-4].lower(),
            "{photo_corr}": get_pds3("CH1:PHOTOMETRY_CORR_FILE_NAME")[
                            :-4].lower(),
            "{solar_spec}": get_pds3("CH1:SOLAR_SPECTRUM_FILE_NAME")[
                            :-4].lower(),
            "{thermal_correction_flag}": "true"
            if get_pds3("CH1:THERMAL_CORRECTION_FLAG") == "Y"
            else "false",
        }
        generic_dictionary = m3_generic_tags(self.LABEL)
        orientation_dictionary = m3_orientation_tags(self.LABEL)
        latlon_dictionary = m3_latlon_tags(self)

        return merge(
            l2_dictionary,
            generic_dictionary,
            orientation_dictionary,
            latlon_dictionary,
        )

    def write_pds4(
            self,
            output_directory,
            write_product_files=True,
            write_label_file=True,
            clean=False
    ):
        """
        output file objects and label for a PDS4 product corresponding to
        this object.
        (string containing output directory -> None)
        """
        print("Converting " + self.filename + " to PDS4.")
        self.rfl_file = output_directory + self.pds4_root + "_rfl.fits"
        self.sup_file = output_directory + self.pds4_root + "_sup.fits"
        if write_product_files:
            self.fits_rfl_image.writeto(self.rfl_file, overwrite=True)
            self.fits_sup_image.writeto(self.sup_file, overwrite=True)
            if clean:
                del self.fits_rfl_image
                del self.fits_sup_image
        self.convert_label(
            output_directory, write_label_file, label_name=self.pds4_root
        )


"""
Note that we do not even apply _pdr_ to any of these calibration images. This
is basically because no useful product-level metadata is given in the PDS3
archive for these files. They do not have PDS3 labels; their ENVI headers are
minimal and contain only array format specifications. It is a waste of time
to do anything but transform them to _numpy_ arrays as quickly as possible.
"""


class M3BDEWriter(PDS4Writer):
    """
    implements business logic for writing PDS4 versions of M3 BDE files.
    basically identical to the flat field writer below.
    """

    def __init__(
            self, filename, *,
            template="./labels/m3/bad_detector_element_template.xml"
    ):
        self.filename = None
        self.template = template
        self.fits_image_file = None

        super().__init__(filename)

        envi_img = rasterio.open(self.filename).read(1)
        self.FITS_IMAGE = fitsify(envi_img)

        self.pds4_root = (
                interpret_m3_basename(self.filename)[
                    "basename"].lower() + "_bde"
        )

    def generate_tag_mapping(self):
        """
        make a dictionary of mappings to tags in PDS4 label template.
        """
        m3_info = interpret_m3_basename(self.filename)
        return {
            "{basename}": m3_info["basename"],
            "{basename_lower}": m3_info["basename"].lower(),
            "{nominal_product_time}": m3_info["time"],
            "{file_records}": 260 if m3_info["mode"] == "target" else 86,
            "{mode_samples}": 640 if m3_info["mode"] == "target" else 320,
            "{mode_lines}": 260 if m3_info["mode"] == "target" else 86,
            "{mode_file_size}": 671040 if m3_info[
                                              "mode"] == "target" else 115200,
        }

    def write_pds4(
            self,
            output_directory,
            write_product_files=True,
            write_label_file=True,
    ):
        """
        output file objects and label for a PDS4 product corresponding to
        this object.
        (string containing output directory -> None)
        """
        print("Converting " + self.filename + " to PDS4.")

        self.fits_image_file = output_directory + self.pds4_root + ".fits"
        if write_product_files:
            # these are 2D images; they have a single 'band' to rasterio

            self.FITS_IMAGE.writeto(self.fits_image_file, overwrite=True)
        self.write_label(output_directory, write_label_file,
                         label_name=self.pds4_root)


class M3FlatFieldWriter(PDS4Writer):
    """
    implements business logic for writing PDS4 versions of M3 flat field files
    """

    def __init__(self, filename, *,
                 template="./labels/m3/flat_field_template.xml"):
        self.filename = None
        self.logfile = None
        self.fits_image_file = None
        self.FITS_IMAGE = np.array([])

        super().__init__(filename)

        self.template = template
        self.pds4_root = (
                interpret_m3_basename(self.filename)[
                    "basename"].lower() + "_ff"
        )

    def generate_tag_mapping(self):
        """
        make a dictionary of mappings to tags in PDS4 label template.
        """
        m3_info = interpret_m3_basename(self.filename)
        return {
            "{basename}": m3_info["basename"],
            "{basename_lower}": m3_info["basename"].lower(),
            "{nominal_product_time}": m3_info["time"],
            "{mode_samples}": 640 if m3_info["mode"] == "target" else 320,
            "{mode_lines}": 260 if m3_info["mode"] == "target" else 86,
            "{mode_file_size}": 671040 if m3_info[
                                              "mode"] == "target" else 115200,
        }

    def write_pds4(
            self,
            output_directory,
            write_product_files=True,
            write_label_file=True,
    ):
        """
        output file objects and label for a PDS4 product corresponding to
        this object.
        (string containing output directory -> None)
        """
        print("Converting " + self.filename + " to PDS4.")
        # all of the images we need to convert in this way seem to have ENVI
        # headers that are handled well by rasterio; moreover, since they
        # don't have PDS3
        # labels, we can't assemble a struct format specification without
        # referencing
        # the ENVI headers _anyway_, so just using rasterio.

        self.fits_image_file = output_directory + self.pds4_root + ".fits"
        if write_product_files:
            # these are 2D images; they have a single 'band' to rasterio
            envi_img = rasterio.open(self.filename).read(1)
            self.FITS_IMAGE = fitsify(envi_img)
            print("Writing image to " + self.fits_image_file)
            self.FITS_IMAGE.writeto(self.fits_image_file, overwrite=True)
        self.write_label(output_directory, write_label_file,
                         label_name=self.pds4_root)


class M3PipelineLogWriter(PDS4Writer):
    """
    implements business logic for writing PDS4 versions of M3 reduction
    pipeline logs
    """

    def __init__(
            self, filename, *,
            template="./labels/m3/reduction_pipeline_log_template.xml"
    ):
        self.filename = None
        self.template = template
        self.logfile = None

        super().__init__(filename)
        self.pds4_root = (
                interpret_m3_basename(self.filename)[
                    "basename"].lower() + "_log"
        )

    def generate_tag_mapping(self):
        """
        make a dictionary of mappings to tags in PDS4 label template.
        """
        m3_info = interpret_m3_basename(self.filename)
        return {"{basename_lower}": m3_info["basename"].lower()}

    def write_pds4(
            self,
            output_directory,
            write_product_files=True,
            write_label_file=True,
    ):
        """
        output file objects and label for a PDS4 product corresponding to
        this object.
        (string containing output directory -> None)
        """

        self.logfile = output_directory + self.pds4_root + ".txt"
        if write_product_files:
            print("Copying log to " + self.logfile)
            shutil.copyfile(self.filename, self.logfile)
        self.write_label(output_directory, write_label_file,
                         label_name=self.pds4_root)


class M3SSCWriter(PDS4Writer):
    """
    implements business logic for writing PDS4 versions of M3 smooth shape
    curve labels
    """

    def __init__(self, filename, *, template="./labels/m3/ssc_template.xml"):
        self.filename = None
        self.logfile = None

        super().__init__(filename)
        self.template = template
        self.pds4_root = (
                interpret_m3_basename(self.filename)[
                    "basename"].lower() + "_ssc"
        )

    def generate_tag_mapping(self):
        """
        make a dictionary of mappings to tags in PDS4 label template.
        """
        m3_info = interpret_m3_basename(self.filename)
        return {"{basename_lower}": m3_info["basename"].lower()}

    def write_pds4(
            self,
            output_directory,
            write_product_files=True,
            write_label_file=True,
    ):
        """
        output file objects and label for a PDS4 product corresponding to
        this object.
        (string containing output directory -> None)
        """
        self.logfile = output_directory + self.pds4_root + ".txt"
        if write_product_files:
            print("Copying SSC to " + self.logfile)
            shutil.copyfile(self.filename, self.logfile)
        self.write_label(output_directory, write_label_file,
                         label_name=self.pds4_root)


class M3BrowseWriter(PDS4Writer):
    """
    implements business logic for writing M3 browse labels.
    Probably unnecessarily complicated.
    """

    def __init__(
            self,
            filename,
            *,
            second_image_path=None,
            third_image_path=None,
            template_directory="./labels/m3/browse_labels/"
    ):
        self.filename = filename
        super().__init__(filename)
        self.basename = interpret_m3_basename(filename)["basename"].lower()
        self.mode = interpret_m3_basename(filename)["mode"]
        if self.mode == 'target':
            if re.search('(B046|B084|B105)', self.filename):
                self.band_name = 'albedo'
            else:
                self.band_name = 'thermal'
        else:
            if 'B046' in self.filename:
                self.band_name = 'albedo'
            else:
                self.band_name = 'thermal'

        if (self.mode == 'target') and (self.band_name == 'albedo'):
            assert third_image_path is not None
            assert second_image_path is not None
        else:
            assert third_image_path is None
            assert second_image_path is None
        self.second_image_path = second_image_path
        self.third_image_path = third_image_path
        self.template = template_directory + \
            "m3_browse_" + \
            self.band_name + \
            ".xml"
        self.output_file_1 = None
        self.output_file_2 = None
        self.output_file_3 = None

    def generate_tag_mapping(self):
        """
        make a dictionary of mappings to tags in PDS4 label template.
        """
        return {
            "{basename}": self.basename,
            "{delete:" + self.mode + "}": True
        }

    def write_pds4(
            self,
            output_directory,
            write_product_files=True,
            write_label_file=True,
    ):
        """
        output file objects and label for a PDS4 product corresponding to
        this object. (string containing output directory -> None)
        """

        if self.mode == 'target':
            if self.band_name == 'thermal':
                self.output_file_1 = self.basename + '_thermal_250.jpg'
            else:
                self.output_file_1 = self.basename + '_albedo_46.jpg'
                self.output_file_2 = self.basename + '_albedo_84.jpg'
                self.output_file_3 = self.basename + '_albedo_105.jpg'

        else:
            if self.band_name == 'thermal':
                self.output_file_1 = self.basename + '_thermal_84.jpg'
            else:
                self.output_file_1 = self.basename + '_albedo_46.jpg'

        if write_product_files:
            print("Copying browse images to " + output_directory)
            shutil.copyfile(
                self.filename,
                output_directory + self.output_file_1
            )
            for file_pair in [
                [self.second_image_path, self.output_file_2],
                [self.third_image_path, self.output_file_3]
            ]:
                if file_pair[1] is None:
                    continue
                shutil.copyfile(
                    file_pair[0],
                    output_directory + file_pair[1]
                )
        self.write_label(
            output_directory,
            write_label_file,
            label_name=self.basename + '_' + self.band_name
        )
