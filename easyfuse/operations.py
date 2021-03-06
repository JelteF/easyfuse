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
import threading

from .filesystem import Directory, File
from .utils import _convert_error_to_fuse_error

# Shows possibly occuring segfaults since llfuse uses the Cython
import faulthandler
faulthandler.enable()


class Operations(LlfuseOperations):
    """The class that implements all file operations.

    Full descriptions of what the operations should do are shown at the
    `llfuse.Operations` documentation.

    Most methods have a ``fh`` or ``inode`` argument. Currently these are the
    same.
    """

    def __init__(self, dir_class=Directory, fs=None, *args,
                 autosync_delay=3, **kwargs):
        """
        Args
        ----
        dir_class: `~.Directory`
            The class that represents directories. This defaults to
            `~.Directory`.

        fs: `dict` or dictlike
            This stores the mapping from an inode number to a `~.File` or
            `~.Directory` object. It defaults to ``{}`` as this is fine in most
            cases. For performance a class could be used  that has a dict like
            interface to another storage option, such as a database.

        autosync_delay: `int` or `float`
            Automatically sync all dirty files after no `~.write` has occured
            for this amount of seconds. If this is set to `None`, autosync will
            be disabled.
        """

        super().__init__(*args, **kwargs)

        if fs is None:
            fs = {}

        self.fs = fs
        self.dir_class = dir_class
        self.autosync_delay = autosync_delay
        self._autosync_lock = threading.RLock()

        self.dir_class('', None, fs=fs, inode=ROOT_INODE)

    _autosync_timer = None

    def fullsync(self):
        """Sync all dirty files using `~.fsync`."""

        fd = os.open(self.mountpoint, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def start_autosync_timer(self):
        """Start an autosync timer and cancel previously enabled ones.

        This is done by calling `~.fsyncdir` on the `llfuse.ROOT_INODE`.
        """
        with self._autosync_lock:
            if self.autosync_delay is not None:
                self.cancel_autosync_timer()
                self._autosync_timer = threading.Timer(self.autosync_delay,
                                                       self.fullsync)
                self._autosync_timer.start()

    def cancel_autosync_timer(self):
        """Cancel a possibly initiated autosync timer."""
        with self._autosync_lock:
            if self._autosync_timer is not None:
                self._autosync_timer.cancel()

    def destroy(self):
        """Execute all pending operations before unmount.

        This currently calls `~.cancel_autosync_timer` and and does a
        `~.fullsync`.
        """
        self.cancel_autosync_timer()
        self.fsyncdir(ROOT_INODE, True)

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
            entry = parent
        elif name == '..':
            entry = parent.parent
        else:
            try:
                entry = parent.children[name]
            except KeyError:
                logging.debug('not found')
                raise FUSEError(errno.ENOENT)

        entry.lookup_count += 1
        return entry

    def access(self, inode, mode, ctx=None):
        """Let everybody access everything.

        TODO: Maybe implement access rights.
        """
        logging.debug('access %s', self.fs[inode])
        return True

    def opendir(self, inode, ctx=None):
        """Return a filehandler equal to the requested inode."""
        logging.debug('opendir %s', inode)
        return inode

    def open(self, inode, flags, ctx=None):
        """Return a filehandler equal to the inode.

        TODO: Decide if something needs to be done with the flags
        """
        logging.debug('open %s %s', self.fs[inode], flags)
        return inode

    def mkdir(self, parent_inode, name, mode, ctx):
        """A basic implementation of the `llfuse.Operations.mkdir` method.

        It uses the ``dir_class`` argument passed to ``__init__``.
        """
        logging.debug('mkdir %s', name)
        entry = self.dir_class(os.fsdecode(name), self.fs[parent_inode])
        entry.lookup_count += 1
        return entry

    def create(self, parent_inode, name, mode, flags, ctx=None):
        """A basic implementation of the `llfuse.Operations.create` method.

        This method uses `illegal_filename` and `get_file_class`.

        """
        logging.debug('create %s %s', parent_inode, name)
        parent = self.fs[parent_inode]
        name = os.fsdecode(name)
        if self.illegal_filename(name):
            # Raise read only filesystem error for forbidden files
            logging.info('File called %s was not created', name)
            raise FUSEError(errno.EROFS)

        file_class = self.get_file_class(name)
        entry = file_class(name, parent)

        entry.lookup_count += 1
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

        It reads bytes from the `~.File.content` attribute of the selected
        `~.File`.
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
        self.cancel_autosync_timer()
        file = self.fs[inode]
        original = file.content

        file.content = original[:offset] + buf + original[offset + len(buf):]
        file.update_modified()

        self.start_autosync_timer()
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

        with _convert_error_to_fuse_error('deleting', entry.path):
            entry.delete()

        del parent.children[name]

        if entry.lookup_count == 0:
            del self.fs[inode]

    def rmdir(self, parent_inode, name, ctx=None):
        """A basic implementation of the `llfuse.Operations.rmdir` method."""
        logging.debug('rmdir')

        parent = self.fs[parent_inode]

        name = os.fsdecode(name)
        entry = parent.children[name]
        inode = entry.inode

        if entry.children:
            raise FUSEError(errno.ENOTEMPTY)

        with _convert_error_to_fuse_error():
            entry.delete()

        del parent.children[name]

        if entry.lookup_count == 0:
            del self.fs[inode]

    def fsync(self, fh, datasync):
        """A basic implementation of the `llfuse.Operations.fsync` method."""
        logging.debug('fsync %s %s', fh, datasync)
        self.fs[fh].fsync()

    def fsyncdir(self, fh, datasync):
        """Same as `~.fsyncdir` but for directories."""
        logging.debug('fsyncdir %s %s', fh, datasync)
        self.fs[fh].fsync()

    def forget(self, inode_list):
        """A basic implementation of the `llfuse.Operations.forget` method."""
        logging.debug('forget %s', inode_list)

        for inode, nlookup in inode_list:
            entry = self.fs[inode]
            entry.lookup_count -= nlookup
            if entry.lookup_count == 0 and entry.deleted:
                del self.fs[inode]
