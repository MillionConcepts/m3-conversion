"""
utilities for converter. most of these are drawn from the mtools suite.
whether to maintain this local version is a decision for later.
"""
import os
from functools import partial, reduce
from operator import getitem, contains, and_, eq, ge, le
import re
from typing import Iterable, Callable

from astropy.io import fits


# ANSI FIGlet 'Electronic'
#   ▄         ▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄            ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄
#  ▐░▌       ▐░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░▌          ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌
#  ▐░▌       ▐░▌ ▀▀▀▀█░█▀▀▀▀  ▀▀▀▀█░█▀▀▀▀ ▐░▌           ▀▀▀▀█░█▀▀▀▀  ▀▀▀▀█░█▀▀▀▀  ▀▀▀▀█░█▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀
#  ▐░▌       ▐░▌     ▐░▌          ▐░▌     ▐░▌               ▐░▌          ▐░▌          ▐░▌     ▐░▌          ▐░▌
#  ▐░▌       ▐░▌     ▐░▌          ▐░▌     ▐░▌               ▐░▌          ▐░▌          ▐░▌     ▐░█▄▄▄▄▄▄▄▄▄ ▐░█▄▄▄▄▄▄▄▄▄
#  ▐░▌       ▐░▌     ▐░▌          ▐░▌     ▐░▌               ▐░▌          ▐░▌          ▐░▌     ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌
#  ▐░▌       ▐░▌     ▐░▌          ▐░▌     ▐░▌               ▐░▌          ▐░▌          ▐░▌     ▐░█▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀█░▌
#  ▐░▌       ▐░▌     ▐░▌          ▐░▌     ▐░▌               ▐░▌          ▐░▌          ▐░▌     ▐░▌                    ▐░▌
#  ▐░█▄▄▄▄▄▄▄█░▌     ▐░▌      ▄▄▄▄█░█▄▄▄▄ ▐░█▄▄▄▄▄▄▄▄▄  ▄▄▄▄█░█▄▄▄▄      ▐░▌      ▄▄▄▄█░█▄▄▄▄ ▐░█▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄█░▌
#  ▐░░░░░░░░░░░▌     ▐░▌     ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌     ▐░▌     ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌
#   ▀▀▀▀▀▀▀▀▀▀▀       ▀       ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀       ▀       ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀


# generic functional utilities


def get_from(collection, keys, default=None):
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


def get_from_and_apply(collection, default_func=str):
    """
    get item from a hierarchy of keys and apply some function to it,
    by default str.

    (collection, f -> f(item of collection, possibly from a nested collection))
    """

    def convert_value_from_collection_corresponding_to(*args,
                                                       func=default_func):
        return func(get_from(collection, args))

    return convert_value_from_collection_corresponding_to


def get_method(method_name):
    """
    generate function that returns method corresponding to method_name of its
    single argument. (name_of_method -> f; f(whatever) -> whatever.name_of_method)
    """

    def get_it_from(whatever):
        return getattr(whatever, method_name)

    return get_it_from


def in_me(container):
    """returns function that checks if all its arguments are in container"""
    inclusion = partial(contains, container)

    def is_in(*args):
        return reduce(and_, map(inclusion, args))

    return is_in


def are_in(items: Iterable, oper: Callable = and_) -> Callable:
    """
    iterable -> function
    returns function that checks if its single argument contains all
    (or by changing oper, perhaps any) items
    """

    def in_it(container: Iterable) -> bool:
        inclusion = partial(contains, container)
        return reduce(oper, map(inclusion, items))

    return in_it


def is_key_it(thing, key):
    def key_is_it(other_thing):
        if eq(thing, other_thing[key]):
            return True
        return False

    return key_is_it


def all_equal(iterable):
    """are all elements of the iterable equal?"""
    iterator = iter(iterable)
    first = next(iterator)
    for item in iterator:
        if not item == first:
            return False
    return True


# pandas utilities


def rows(dataframe):
    """splits row-wise into a list of numpy arrays"""
    return [dataframe.loc[row] for row in dataframe.index]


def columns(dataframe):
    """splits column-wise into a list of numpy arrays"""
    return [dataframe.loc[:, column] for column in dataframe.columns]


def cloc(df, column, op, comparison):
    """ "
    wrapper: 'comparative loc.' returns rows of df where (column op
    comparison) is true (meaning member of column as compared to (generally
    scalar) comparison value). 'op' should be the functional form of the operator,
    as found in the operator module or written in some other way. this is more
    attractive and tractable than the df.loc[df[column] op comparison] pattern.
    doesn't work with some operators, like operator.contains, because of how they
    perform truth testing (see inloc below using in_me rather than contains to
    check  set inclusion of column elements). at present works only on dyadic
    operators.
    """
    return df.loc[op(df[column], comparison)]


def geloc(df, column, comparison):
    """return rows of df where column >= comparison"""
    return cloc(df, column, ge, comparison)


def leloc(df, column, comparison):
    """return rows of df where column <= comparison"""
    return cloc(df, column, le, comparison)


def eqloc(df, column, comparison):
    """return rows of df where column == comparison"""
    return cloc(df, column, eq, comparison)


def inloc(df, column, target_set):
    """return rows of df where column is in target_set"""
    return df.loc[df[column].apply(in_me(target_set))]


def contloc(df, column, target_set):
    """return rows of df where all members of target_set are in column"""
    return df.loc[df[column].apply(are_in(target_set))]


def reloc(frame, column, pattern, flags=re.IGNORECASE, method="contains"):
    """
    return rows of frame where the regex pattern is contained in column
    set method to "match" to just check beginnings of strings
    this is case-insensitive by default; adjust flags to modify that
    """
    regex = re.compile(pattern, flags=flags)
    re_method = getattr(getattr(frame[column], 'str'), method)
    return frame.loc[re_method(regex)]


# uncategorized

def name_root(filename):
    """
    (str -> str); filename, not including extension, from a full file path
    """
    return os.path.splitext(os.path.basename(filename))[0]


def path_stem(filename):
    """
    (str -> str); just the directory tree part from a full file path
    """
    return os.path.split(filename)[0] + "/"


def null_bytes_to_na(string):
    """
    (str -> str) replace strings of only null bytes (\x00) with "n/a".
    for M3L0 line prefix tables.
    """
    if all([char == "\x00" for char in string]):
        return "n/a"
    return string


def fitsify(array):
    return fits.HDUList(fits.PrimaryHDU(array))
