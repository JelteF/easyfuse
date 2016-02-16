"""
This module implements the some simple utilitiy functions.

..  :copyright: (c) 2016 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

from llfuse import FUSEError

from contextlib import contextmanager
import errno
import logging
import traceback


@contextmanager
def _convert_error_to_fuse_error(action, thing):
    try:
        yield
    except Exception as e:
        if isinstance(e, FUSEError):
            raise e
        logging.error('Something went wrong when %s %s: %s', action, thing, e)
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            # DEBUG logging, print stacktrace
            traceback.print_exc()
        raise FUSEError(errno.EAGAIN)
