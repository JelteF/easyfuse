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
from .utils import _convert_error_to_fuse_error


class BaseEntry(EntryAttributes):
    """The base class that all filesystem classes should subclass.

    This is a subclass `llfuse.EntryAttributes` and its attributes that are
    required to have a working filesystem are implemented. Most others are not
    actually implemented currently.
    """

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
            the instance that creates this entry.

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

    _prints = ('path', 'inode', )

    _dirty = False

    #: The amount of times this entry has been looked up by the kernel.
    #: This is increased by a couple of methodes called on `~.Operations` by
    #: normal filesystem operations.
    lookup_count = 0

    #: Indicates if the entry has been deleted.
    deleted = False

    @property
    def inode(self):
        """The inode number.

        This is simply an alias for `~.llfuse.EntryAttributes.st_ino` with a
        clearer name.
        """
        return self.st_ino

    @inode.setter
    def inode(self, value):
        self.st_ino = value

    @property
    def modified(self):
        """The moment of last modification of the entry.

        This is measured in seconds since the UNIX epoch.
        """
        return self.st_mtime_ns / 10**9

    @modified.setter
    def modified(self, value):
        value *= 10**9
        self.st_atime_ns = value
        self.st_ctime_ns = value
        self.st_mtime_ns = value

    @property
    def dirty(self):
        """Indicates if this entry has been changed but not synced."""
        return self._dirty

    @dirty.setter
    def dirty(self, value):
        self._dirty = value
        if value is True and self.parent is not None:
            self.parent.dirty_children = True

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

    def delete(self):
        """Basic deletion operations.

        Override this when code needs to be executed on deletion. Keep calling
        this one by using `super` though, since it does some internal things.
        """
        logging.info('Deleting %s', self.path)
        self.deleted = True

    def save(self):
        """Dummy save method.

        Override this when code needs to be executed when a file is saved.
        """
        logging.info('Saving %s', self.path)

    def fsync(self):
        """Save the entry if it is `~.BaseEntry.dirty`."""
        if self.dirty:
            with _convert_error_to_fuse_error('saving', self.path):
                self.save()
            self.dirty = False


class File(BaseEntry):
    """A class that represents a filesystem file.

    If a file is supposed to be synced, set the ``content`` attribute to `None`
    after initialization.
    """

    def __init__(self, *args, **kwargs):
        r"""
        Args
        ----
        \*args:
            Positional arguments that are passed to the initialization of
            `BaseEntry`.
        \*\*kwargs:
            Keyword arguments that are passed to the initialization of
            `BaseEntry`.
        """

        super().__init__(*args, **kwargs)

        self.st_mode |= stat.S_IFREG

        self.content = b''

    @property
    def content(self):
        """The content of this file in bytes."""
        if self._content is None:
            with _convert_error_to_fuse_error('refreshing content of',
                                              self.path):
                self.refresh_content()
        return self._content

    @content.setter
    def content(self, value):
        self.dirty = value is not None
        self._content = value

        if value is not None:
            self.st_size = len(self._content)


class Directory(BaseEntry):
    """A class that represents a directory in the filesystem."""

    _children = None
    _dirty_children = False

    def __init__(self, *args, **kwargs):
        r"""
        Args
        ----
        \*args:
            Positional arguments that are passed to the initialization of
            `BaseEntry`.
        \*\*kwargs:
            Keyword arguments that are passed to the initialization of
            `BaseEntry`.
        """

        super().__init__(*args, **kwargs)

        # mode = drwxr-xr-x
        self.st_mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH | \
            stat.S_IFDIR

    @property
    def children(self):
        """A `dict` of the children of the directory."""
        if self._children is None:
            with _convert_error_to_fuse_error('refreshing children of',
                                              self.path):
                self.refresh_children()
        return self._children

    @property
    def path(self):
        """The full path of this directory from the mount directory."""
        return super().path + '/'

    @property
    def dirty_children(self):
        """Indicates if the `~.children` need to be synced.

        It is set to `True` if a child of this directory is `~.BaseEntry.dirty`
        or has `~.dirty_children` itself.
        """
        return self._dirty_children

    @dirty_children.setter
    def dirty_children(self, value):
        self._dirty_children = value
        if value is True and self.parent is not None:
            self.parent.dirty_children = True

    def refresh_children(self):
        """Initialize children as an empty `dict`.

        This method should be overloaded by every implementing class, since the
        actual children should obviously be added as well.
        This method should still be called using `super` though.
        """
        self._children = {}

    def fsync(self):
        """Save this entry and `~.BaseEntry.fsync` its children.

        Saving is only done if this entry is `~.BaseEntry.dirty` and syncing
        the children is only done if `~.dirty_children` is `True`.
        """
        super().fsync()

        if self.dirty_children:
            for c in self.children.values():
                c.fsync()

            self.dirty_children = False
