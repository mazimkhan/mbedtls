#! /usr/bin/env sh

# cleanup.sh
#
# This file is part of mbed TLS (https://tls.mbed.org)
#
# Copyright (c) 2018, ARM Limited, All Rights Reserved



################################################################
#### Documentation
################################################################

# Purpose
# -------
#
# To perform cleanup by removing cmake generated build files and
# restoring config.
#

# Abort on errors (and uninitialised variables)
set -eu

CONFIG_H='include/mbedtls/config.h'
CONFIG_BAK="$CONFIG_H.bak"

# remove built files as well as the cmake cache/config

command make clean

find . -name yotta -prune -o -iname '*cmake*' -not -name CMakeLists.txt -exec rm -rf {} \+
rm -f include/Makefile include/mbedtls/Makefile programs/*/Makefile
git update-index --no-skip-worktree Makefile library/Makefile programs/Makefile tests/Makefile
git checkout -- Makefile library/Makefile programs/Makefile tests/Makefile

if [ -f "$CONFIG_BAK" ]; then
    mv "$CONFIG_BAK" "$CONFIG_H"
fi
