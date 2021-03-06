easyfuse
========

Easyfuse is a Python library to allow easy mapping from filesystem operations
to any backend. My initial use case was to edit dokuwiki pages and add
attachements from the command line.


Installation
------------
.. highlight:: bash

Before installing the library itself be sure to install the system
dependencies. For Ubuntu these should be enough:

::

    sudo apt-get install libattr1-dev libfuse-dev
    # Python 2 developement headers (needed when using Python 2)
    sudo apt-get install python-dev
    # Python 3 developement headers (needed when using Python 3)
    sudo apt-get install python3-dev




PyLaTeX works on Python 2.7 and 3.3+ and it is simply installed using pip:

::

    pip install easyfuse


Support
-------

This library is being developed in and for Python 3. Because of a conversion
script the current version also works in Python 2.7. For future versions, no
such promise will be made. Python 3 features that are useful but incompatible
with Python 2 will be used. If you find a bug for Python 2 and it is fixable
without ugly hacks feel free to send a pull request.

This library is developed for Linux. I have no intention to write fixes or test
for platform specific bugs with every update, especially since I have no other
operating systems to test it on. Pull requests that fix those issues are always
welcome though.

Contributing
------------
Read the :doc:`contributing` page for tips and rules when you want to
contribute. To just see the source code, you should go to the `Github
repository <https://github.com/JelteF/easyfuse/>`_.




.. toctree::
    :maxdepth: 1
    :glob:
    :hidden:

    usage
    api
    changelog
    contributing




Indices
-------

* :ref:`genindex`
* :ref:`modindex`
