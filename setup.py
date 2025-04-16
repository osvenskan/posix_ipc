import setuptools
from setuptools.extension import Extension
import sys

# When python -m build runs, sys.path contains a minimum of entries. I add the current directory
# to it (which is guaranteed by setuptools to be the project's root) so that I can import my
# build_support tools.
sys.path.append('.')
import build_support.discover_system_info

# As of April 2025, specifying the license metadata here (rather than in pyproject.toml) seems
# like the best solution for now. See https://github.com/osvenskan/posix_ipc/issues/68
LICENSE = "BSD-3-Clause"

# As of April 2025, use of tool.setuptools.ext-modules is stil experimental in pyproject.toml.
# Also, this code needs to dynamically adjust the `libraries` value that's passed to setuptools,
# so I can't get rid of setup.py just yet.
SOURCE_FILES = ["src/posix_ipc_module.c"]
DEPENDS = ["src/posix_ipc_module.c", "src/system_info.h"]

libraries = []

system_info = build_support.discover_system_info.discover()

# Linux & FreeBSD require linking against the realtime libs.
# This causes an error on other platforms
if "REALTIME_LIB_IS_NEEDED" in system_info:
    libraries.append("rt")

ext_modules = [Extension("posix_ipc",
                         SOURCE_FILES,
                         libraries=libraries,
                         depends=DEPENDS,
                         # -E is useful for debugging compile errors.
                         # extra_compile_args=['-E'],
                         )]

setuptools.setup(ext_modules=ext_modules,
                 license=LICENSE,
                 )
