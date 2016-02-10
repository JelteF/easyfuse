"""
This module implements the class that deals with operations from llfuse.

..  :copyright: (c) 2016 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

from llfuse import Operations as LlfuseOperations
from llfuse import ROOT_INODE

from .filesystem import Directory


class Operations(LlfuseOperations):
    """The class that implements all file operations."""

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
