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
    """The class that implements all file operations.

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
        parent = directory.parent

        if parent is None:
            # For the ROOT_INODE the parent is itself, this seems to work for
            # some weird reason.
            parent = directory

        special_entries = []
        if directory.inode > offset:
            special_entries.append((os.fsencode('.'),
                                    directory,
                                    directory.inode))
        if parent and parent.inode > offset:
            special_entries.append((os.fsencode('..'),
                                    parent,
                                    parent.inode))

        entries = [(os.fsencode(c.name), c, c.inode) for c in
                   directory.children.values() if c.inode > offset]
        entries += special_entries
        entries = sorted(entries, key=lambda x: x[2])

        return entries

    def lookup(self, parent_inode, name, ctx=None):
        """A basic implementation `llfuse.Operations.lookup` method.

        This currently does not do anything special for the
        `~llfuse.ROOT_INODE`, but it seems to work anyway.
        """
        logging.debug('lookup %s', name)

        name = os.fsdecode(name)
        parent = self.fs[parent_inode]

        if name == '.':
            return parent
        if name == '..':
            return parent.parent

        try:
            return parent.children[name]
        except KeyError:
            logging.debug('not found')
            raise FUSEError(errno.ENOENT)

    def access(self, inode, mode, ctx=None):
        """Let everybody access everything.

        TODO: Maybe implement access rights.
        """
        logging.debug('access %s', self.fs[inode])
        return True

    def opendir(self, inode, ctx=None):
        """Return a filehandler equal to the requested inode.

        TODO: Count accesses
        """
        logging.debug('opendir %s', inode)
        return inode

    def open(self, inode, flags, ctx=None):
        """Return a filehandler equal to the inode.

        TODO: Count accesses
        TODO: Decide if something needs to be done with the flags
        """
        logging.debug('open %s %s %s', self.fs[inode], flags)
        return inode

    def mkdir(self, parent_inode, name, mode, ctx):
        logging.debug('mkdir %s', name)
        return self.dir_class(os.fsdecode(name), self.fs,
                              self.fs[parent_inode])
