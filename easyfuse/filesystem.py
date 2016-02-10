"""
This module implements the classes that map to filesystem objects.

..  :copyright: (c) 2016 by Jelte Fennema.
    :license: MIT, see License for more details.
"""
from llfuse import EntryAttributes
from uuid import uuid4
import os
import stat
import time

import logging


class BaseEntry(EntryAttributes):
    """The base class that all filesystem classes should subclass."""

    _prints = ('path', 'inode', )

    @property
    def inode(self):
        """The inode number.

        This is simply an alias for `st_ino` with a clearer name.
        """
        return self.st_ino

    @inode.setter
    def inode(self, value):
        self.st_ino = value

    def __init__(self, name, fs, parent, *, inode=None):
        """
        Args
        ----
        name: str
            The name of the entry.
        fs: `dict` or dictlike
            This stores the mapping from an inode number to a `~.File` or
            `~.Directory` object. The newly created `BaseEntry` will be added
            to this as well. It should most likely be the ``fs`` attribute of
            the instance that made created this instance.

        parent: `~.Directory`
            The filesystem parent of this
        inode: int
            An explicit inode number. If it is `None` a new number will
            automatically be generated. Only in rare cases this automatic
            generation is not sufficient, so use this only when really
            necassary.
        """

        logging.info('Creating a %s called: %s',
                     self.__class__.__name__.lower(),
                     name)

        super().__init__()

        self.name = name
        self.fs = fs
        self.parent = parent

        self.update_modified()

        # Files belong to the current user
        self.st_uid = os.getuid()
        self.st_gid = os.getgid()

        # mode = -rw-r--r--
        self.st_mode = stat.S_IRUSR | stat.S_IWUSR | \
            stat.S_IRGRP | stat.S_IROTH

        if inode is None:
            inode = self.generate_inode_number()

        self.inode = inode

        self.fs[self.inode] = self

        if parent is not None:
            parent.children[self.name] = self

    def __repr__(self):
        string = '<%s(' % self.__class__.__name__
        for i, attr in enumerate(self._prints):
            if i:
                string += ', '
            string += repr(getattr(self, attr))
        string += ', '
        string += stat.filemode(self.st_mode)

        string += ')>'
        return string

    def generate_inode_number(self):
        """Generate a unique inode number.

        By default this is done by taking part of the result of uuid4. This
        method can be overridden if another method is preferred.
        """

        inode = uuid4().int & (1 << 32)-1
        while inode in self.fs:
            inode = uuid4().int & (1 << 32)-1
        return inode

    def update_modified(self):
        """Update the modified time to the current time."""
        self.modified = time.time()

    @property
    def modified(self):
        return self.st_mtime_ns / 10**9

    @modified.setter
    def modified(self, value):
        value *= 10**9
        self.st_atime_ns = value
        self.st_ctime_ns = value
        self.st_mtime_ns = value

    @property
    def path(self):
        """The full path of this entry from the mount directory."""
        return '/'.join([p.name for p in self.parents] + [self.name])

    @property
    def parents(self):
        """Recursively get the parents of this entry."""
        if self.parent is None:
            return []
        return self.parent.parents + [self.parent]

    @property
    def depth(self):
        """The depth of the entry in the directory tree.

        This basically counts the number of parents this entry has.
        """
        return len(self.parents)

    def delete(self):
        """Dummy delete method.

        Override this when code needs to be executed on deletion.
        """
        logging.info('Deleting %s', self.path)

    def save(self):
        """Dummy save method.

        Override this when code needs to be executed when a file is saved.
        """
        logging.info('Saving %s', self.path)


class File(BaseEntry):
    """A class that represents a filesystem file."""

    def __init__(self, *args, **kwargs):
        """
        Args
        ----
        *args and **kwargs:
            Arguments that are passed to the initialization of `BaseEntry`.
        """

        super().__init__(*args, **kwargs)

        self.st_mode |= stat.S_IFREG

        self.content = b''


class LazyFile(File):
    """A class that represents a file that has lazy content loading.

    If a file is supposed to be synced, set the ``content`` attribute to `None`
    after initialization.
    """

    @property
    def content(self):
        if self._content is None:
            self.refresh_content()
        return self._content

    @content.setter
    def content(self, value):
        self._content = value


class Directory(BaseEntry):
    """A class that represents a directory in the filesystem."""

    _children = None

    def __init__(self, *args, **kwargs):
        """
        Args
        ----
        *args and **kwargs:
            Arguments that are passed to the initialization of `BaseEntry`.
        """

        super().__init__(*args, **kwargs)

        # mode = drwxr-xr-x
        self.st_mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH | \
            stat.S_IFDIR

    @property
    def children(self):
        """A `dict` of the children of the directory."""
        if self._children is None:
            self.refresh_children()
        return self._children

    def refresh_children(self):
        """Initialize children as an empty `dict`.

        This method should be overloaded by every implementing class, since the
        actual children should obviously be added as well.
        This method should still be called using `super` though.
        """
        self._children = {}

    @property
    def path(self):
        """The full path of this directory from the mount directory."""
        return super().path + '/'
