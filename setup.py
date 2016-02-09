try:
    from setuptools import setup
    from setuptools.command.install import install
    from setuptools.command.egg_info import egg_info
except ImportError:
    from distutils.core import setup
import sys
import os
import subprocess
import errno


if sys.version_info[:2] <= (2, 6):
    raise RuntimeError(
        "You're using Python <= 2.6, but this package requires either Python "
        "2.7, or 3.3 or above, so you can't use it unless you upgrade your "
        "Python version."
    )

dependencies = ['llfuse']

extras = {
    'docs': ['sphinx'],
    'testing': ['flake8', 'pep8-naming', 'flake8_docstrings', 'nose'],
    'convert_to_py2': ['3to2', 'future'],
}

if sys.version_info[0] == 3:
    source_dir = '.'
else:
    source_dir = 'python2_source'
    dependencies.append('future')

PY2_CONVERTED = False


extras['all'] = list(set([req for reqs in extras.values() for req in reqs]))


# Automatically convert the source from Python 3 to Python 2 if we need to.
class CustomInstall(install):
    def run(self):
        convert_to_py2()
        install.run(self)


class CustomEggInfo(egg_info):
    def initialize_options(self):
        convert_to_py2()
        egg_info.initialize_options(self)


def convert_to_py2():
    global PY2_CONVERTED
    if source_dir == 'python2_source' and not PY2_CONVERTED:
        try:
            # Check if 3to2 exists
            subprocess.check_output(['3to2', '--help'])
            subprocess.check_output(['pasteurize', '--help'])
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise e
            if not os.path.exists(os.path.join(source_dir, 'easyfuse')):
                raise ImportError('3to2 and future need to be installed '
                                  'before installing when easyfuse for Python '
                                  '2.7 when it is not installed using one of '
                                  'the pip releases.')
        else:
            converter = os.path.dirname(os.path.realpath(__file__)) \
                + '/convert_to_py2.sh'
            subprocess.check_call([converter])
            PY2_CONVERTED = True


setup(name='easyfuse',
      version='0.0.1',
      author='Jelte Fennema',
      author_email='easyfuse@jeltef.nl',
      description='Python library to create a simple FUSE file system',
      long_description=open('README.rst').read(),
      package_dir={'': source_dir},
      packages=['easyfuse'],
      url='https://github.com/JelteF/easyfuse',
      license='MIT',
      install_requires=dependencies,
      extras_require=extras,
      cmdclass={
          'install': CustomInstall,
          'egg_info': CustomEggInfo,
      },
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Filesystems',
      ]
      )
