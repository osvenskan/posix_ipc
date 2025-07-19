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

# Linux requires linking against the realtime libs. My notes say that FreeBSD also required this,
# but it looks like librt on FreeBSD is a raytracing library so maybe not. :-) In any case,
# adding "rt" to the list of linked libraries on platforms where it doesn't exist (e.g. Mac)
# causes a build failure (due to a link error), so I need to be careful about only adding it
# where it's needed.
if system_info['realtime_lib_is_needed']:
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
