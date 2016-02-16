"""
This module implements the some simple utilitiy functions.

..  :copyright: (c) 2016 by Jelte Fennema.
    :license: MIT, see License for more details.
"""
import llfuse
from llfuse import FUSEError

from contextlib import contextmanager
import errno
import logging
import traceback
import os


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


def mount(operations, mountpoint, options=None, *,
          override_default_options=False, workers=30):
    """Mount a file system.

    Args
    ----
    operations: `~.Operations`
        The operations handler for the file system.
    mountpoint: str
        The directory on which the file system should be mounted.
    options: set
        A set of options that should be used when mounting.
    override_default_options: bool
        If this is set to `True` only the supplied options will be used.
        Otherwise the options will be added to the defaults. The defaults are
        the defaults supplied by `llfuse.default_options`.
    workers: int
        The amount of worker threads that should be spawned to handle the file
        operations.
    """

    operations.mountpoint = os.path.abspath(mountpoint)

    if options is None:
        options = llfuse.default_options
    elif not override_default_options:
        options |= llfuse.default_options

    llfuse.init(operations, mountpoint, options)

    try:
        llfuse.main(workers=workers)
    finally:
        llfuse.close()
