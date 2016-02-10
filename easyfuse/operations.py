"""
This module implements the class that deals with operations from llfuse.

..  :copyright: (c) 2016 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

from llfuse import Operations as LlfuseOperations
from llfuse import ROOT_INODE, FUSEError

import logging
import errno
import os

from .filesystem import Directory


class Operations(LlfuseOperations):
    """The class that implements all file operations.i

    Full descriptions of what the operations should do are shown at the
    `llfuse.Operations` documentation.

    Most methods have a ``fh`` or ``inode`` argument. Currently these are the
    same.
    """

    def __init__(self, dir_class=Directory, filesystem=None, *args, **kwargs):
        """
        Args
        ----
        dir_class: `~.Directory`
            The class that represents directories. This defaults to
            `~.Directory`.

        filesystem: `dict` or dictlike
            This stores the mapping from an inode number to a `~.File` or
            `~.Directory` object. It defaults to `{}` as this is fine in most
            cases. For performance a class could be used  that has a dict like
            interface to another storage option, such as a database.

        """

        super().__init__(*args, **kwargs)

        if filesystem is None:
            filesystem = {}

        self.fs = filesystem
        self.dir_class = dir_class

        self.dir_class('', filesystem, None, inode=ROOT_INODE)

    def getattr(self, inode, ctx=None):
        """Basic gettatr method.

        Returns
        -------
        `~.BaseEntry`
            The entry associated with the inode.
        """

        logging.debug('getattr %s', inode)
        try:
            logging.debug('found')
            entry = self.fs[inode]
            return entry
        except KeyError:
            logging.debug('not found')
            raise FUSEError(errno.ENOENT)

    def readdir(self, fh, offset):
        """A basic implementation `llfuse.Operations.readdir` method."""
        logging.debug('readdir %s %s', fh, offset)
        directory = self.getattr(fh)
        special_entries = []
        if directory.inode > offset:
            special_entries.append((os.fsencode('.'),
                                    directory,
                                    directory.inode))
        # TODO: Add a .. entry as well.
        entries = [(os.fsencode(c.name), c, c.inode) for c in
                   directory.children.values() if c.inode > offset]
        entries += special_entries
        entries = sorted(entries, key=lambda x: x[2])

        return entries
