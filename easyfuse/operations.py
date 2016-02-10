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

from .filesystem import Directory, File


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
        """A basic implementation of the `llfuse.Operations.mkdir` method.

        It uses the ``dir_class`` argument passed to ``__init__``.
        """
        logging.debug('mkdir %s', name)
        return self.dir_class(os.fsdecode(name), self.fs,
                              self.fs[parent_inode])

    def create(self, parent_inode, name, mode, flags, ctx=None):
        """A basic implementation of the `llfuse.Operations.create` method.

        This method uses `check_illegal_filename` and `get_file_class`.

        """
        logging.debug('create %s %s', parent_inode, name)
        parent = self.fs[parent_inode]
        name = os.fsdecode(name)
        if self.illegal_filename(name):
            # Raise read only filesystem error for forbidden files
            logging.info('File called %s was not created', name)
            raise FUSEError(errno.EROFS)

        file_class = self.get_file_class(name)
        entry = file_class(name, self.fs, parent)

        return (entry.inode, entry)

    def illegal_filename(self, name):
        """Return True if filename is illegal.

        By default all filenames are accepted. This method should be overridden
        when this is not the case.
        """
        return False

    def get_file_class(self, name):
        """Return the correct file class based on the filename.

        This can be used to use different clasess for different filenames. By
        default it returns `~.File`
        """
        return File

    def read(self, fh, offset, length):
        """A basic implementation of the `llfuse.Operations.read` method.

        It reads bytes from the ``content`` attribute of the selected entry.
        """
        logging.debug('read %s %s %s', fh, offset, length)
        return self.fs[fh].content[offset: offset + length]

    def setattr(self, inode, attr, fields, fh, ctx=None):
        """A basic implementation of the `llfuse.Operations.setattr` method.

        It currently only supports changing the size of the file.
        """
        logging.debug('setattr %s %s %s', inode, attr, fields)
        entry = self.getattr(inode)
        if fields.update_size:
            if entry.st_size < attr.st_size:
                entry.content = + b'\0' * (attr.st_size - entry.st_size)
            else:
                entry.content = entry.content[:attr.st_size]

        return entry

    def write(self, inode, offset, buf):
        """A basic implementation of the `llfuse.Operations.write` method."""
        logging.debug('write')

        file = self.fs[inode]
        original = file.content

        file.content = original[:offset] + buf + original[offset + len(buf):]
        file.update_modified()
        file.save()
        return len(buf)

    def unlink(self, parent_inode, name, ctx=None):
        """A basic implementation of the `llfuse.Operations.unlink` method.

        This removes files.
        """
        logging.debug('unlink %s', name)
        parent = self.fs[parent_inode]

        name = os.fsdecode(name)
        entry = parent.children[name]
        inode = entry.inode

        entry.delete()
        del self.fs[inode]
        del parent.children[name]

    def rmdir(self, parent_inode, name, ctx=None):
        logging.debug('rmdir')

        parent = self.fs[parent_inode]

        name = os.fsdecode(name)
        entry = parent.children[name]
        inode = entry.inode

        if entry.children:
            raise FUSEError(errno.ENOTEMPTY)

        entry.delete()
        del self.fs[inode]
        del parent.children[name]
