"""
This module implements the some simple utilitiy functions.

..  :copyright: (c) 2016 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

from llfuse import FUSEError

from contextlib import contextmanager
import errno
import logging


@contextmanager
def _convert_error_to_fuse_error(action, thing):
    try:
        yield
    except Exception as e:
        if isinstance(e, FUSEError):
            raise e
        logging.error('Something went wrong when %s %s: %s', action, thing, e)
        raise FUSEError(errno.EAGAIN)
