"""
A Python library to create a simple FUSE file system.

..  :copyright: (c) 2016 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

from .utils import mount
from .operations import Operations
from .filesystem import Directory, File, BaseEntry
