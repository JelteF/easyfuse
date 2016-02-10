#!/bin/bash

git clone --branch=gh-pages `git config --get remote.origin.url` gh-pages
rm -rf _build/html
ln -sf ../gh-pages/dev _build/html
