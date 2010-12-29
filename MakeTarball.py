#!/usr/bin/env python

# Python imports
import time
import tarfile
import os
import hashlib

RSS_TIMESTAMP_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"

f = open("VERSION")
VERSION = f.read().strip()
f.close()

filenames = (
#    "memory_leak_tests.py",
    "LICENSE",
    "INSTALL",
    "README",
    "VERSION",
    "ReadMe.html",
    "history.html",
    "setup.py",
    "prober.py",
    "prober/",
    "prober/sniff_mq_prio_max.c",
    "prober/sniff_realtime_lib.c",
    "prober/sniff_sem_getvalue.c",
    "prober/sniff_sem_timedwait.c",
    "prober/sniff_sem_value_max.c",
    "prober/sniff_page_size.c",
    "prober/sniff_mq_existence.c",
    "posix_ipc_module.c",
    "demo/",
    "demo/ReadMe.txt",
    "demo/SampleIpcConversation.png",
    "demo/cleanup.py",
    "demo/conclusion.c",
    "demo/conclusion.py",
    "demo/md5.c",
    "demo/md5.h",
    "demo/make_all.sh",
    "demo/params.txt",
    "demo/premise.c",
    "demo/premise.py",
    "demo/utils.c",
    "demo/utils.h",
    "demo/utils.py",
    "demo2/ReadMe.txt",
    "demo2/SampleIpcConversation.png",
    "demo2/cleanup.py",
    "demo2/conclusion.py",
    "demo2/premise.py",
    "demo2/utils.py",
    "demo2/params.txt",
)

tarball_name = "posix_ipc-%s.tar.gz" % VERSION
md5_name = "posix_ipc-%s.md5.txt" % VERSION

if os.path.exists(tarball_name):
    os.remove(tarball_name)

SourceDir = "./"
BundleDir = "posix_ipc-%s/" % VERSION

tarball = tarfile.open("./" + tarball_name, "w:gz")
for name in filenames:
    SourceName = SourceDir + name
    BundledName = BundleDir + name

    print "Adding " + SourceName

    tarball.add(SourceName, BundledName, False)
tarball.close()

# Generate the md5 hash of the tarball
f = open("./" + tarball_name)
s = f.read()
f.close()

s = hashlib.md5(s).hexdigest()

print "md5 = " + s

f = open(md5_name, "w")
f.write(s)
f.close()


# Print an RSS item suitable for pasting into rss.xml
timestamp = time.strftime(RSS_TIMESTAMP_FORMAT, time.gmtime())

print """

		<item>
			<guid isPermaLink="false">%s</guid>
			<title>posix_ipc %s Released</title>
			<pubDate>%s</pubDate>
			<link>http://semanchuk.com/philip/posix_ipc/</link>
			<description>Version %s of posix_ipc has been released.
			</description>
		</item>

""" % (VERSION, VERSION, timestamp, VERSION)

