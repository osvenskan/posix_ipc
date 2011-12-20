#!/usr/bin/env python

# Python imports
import time
import tarfile
import os
import hashlib

RSS_TIMESTAMP_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"

VERSION = open("VERSION").read().strip()

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
    "demo3/ReadMe.txt", 
    "demo3/cleanup.py", 
    "demo3/one_shot_signal.py", 
    "demo3/one_shot_thread.py", 
    "demo3/repeating_signal.py", 
    "demo3/repeating_thread.py", 
    "demo3/utils.py", 
)

tarball_name = "posix_ipc-%s.tar.gz" % VERSION
md5_name = "posix_ipc-%s.md5.txt" % VERSION
sha1_name = "posix_ipc-%s.sha1.txt" % VERSION

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
s = open("./" + tarball_name).read()

md5 = hashlib.md5(s).hexdigest()
sha1 = hashlib.sha1(s).hexdigest()

open(md5_name, "wb").write(md5)
open(sha1_name, "wb").write(sha1)

print "md5 = " + md5
print "sha1 = " + sha1


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

