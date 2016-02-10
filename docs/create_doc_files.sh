#!/usr/bin/env bash
# Optional named arguments:
#      -p COMMAND: the python command that should be used, e.g. -p python3

# Default values
python="python"

# Check if a command line argument was provided as an input argument.
while getopts "p:" opt; do
  case $opt in
    p)
      python=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

ARGS='--separate --force --no-headings --no-toc'

echo Cleaning pylatex and examples
rm -rf source/easyfuse/*

sphinx-apidoc -o easyfuse/ ../easyfuse/ $ARGS
echo Removing file easyfuse/easyfuse.rst
rm easyfuse/easyfuse.rst
