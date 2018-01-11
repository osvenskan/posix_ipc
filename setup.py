# Python-ish modules
# setuptools is apparently distributed with python.org Python now. Does that mean it's
# standard? Who knows. I need it to build wheels on my machine, otherwise setup can get by just
# fine with distutils.
try:
    import setuptools as distutools
except ImportError:
    import distutils.core as distutools

# My modules
import prober

VERSION = open("VERSION").read().strip()

name = "posix_ipc"
description = "POSIX IPC primitives (semaphores, shared memory and message queues) for Python"
long_description = open("README").read().strip()
author = "Philip Semanchuk"
author_email = "philip@semanchuk.com"
maintainer = "Philip Semanchuk"
url = "http://semanchuk.com/philip/posix_ipc/"
download_url = "http://semanchuk.com/philip/posix_ipc/posix_ipc-%s.tar.gz" % VERSION
source_files = ["posix_ipc_module.c"]
# http://pypi.python.org/pypi?%3Aaction=list_classifiers
classifiers = ["Development Status :: 5 - Production/Stable",
               "Intended Audience :: Developers",
               "License :: OSI Approved :: BSD License",
               "Operating System :: MacOS :: MacOS X",
               "Operating System :: POSIX :: BSD :: FreeBSD",
               "Operating System :: POSIX :: Linux",
               "Operating System :: POSIX :: SunOS/Solaris",
               "Operating System :: POSIX",
               "Operating System :: Unix",
               "Programming Language :: Python",
               "Programming Language :: Python :: 2",
               "Programming Language :: Python :: 3",
               "Topic :: Utilities"]
license = "http://creativecommons.org/licenses/BSD/"
keywords = "ipc inter-process communication semaphore shared memory shm message queue"

libraries = []

d = prober.probe()

# Linux & FreeBSD require linking against the realtime libs
# This causes an error on other platforms
if "REALTIME_LIB_IS_NEEDED" in d:
    libraries.append("rt")

ext_modules = [distutools.Extension("posix_ipc",
                                    source_files,
                                    libraries=libraries,
                                    depends=["posix_ipc_module.c",
                                             "probe_results.h",
                                             ],
                                    # extra_compile_args=['-E']
                                    )
               ]

distutools.setup(name=name,
                 version=VERSION,
                 description=description,
                 long_description=long_description,
                 author=author,
                 author_email=author_email,
                 maintainer=maintainer,
                 url=url,
                 download_url=download_url,
                 classifiers=classifiers,
                 license=license,
                 keywords=keywords,
                 ext_modules=ext_modules
                 )
