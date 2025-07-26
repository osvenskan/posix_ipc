# Building/Compiling POSIX IPC

You can build `posix_ipc` with a normal build command like `python -m build`. If this works for you, you don't need to read any further. But if you're curious, or the build is not working for you, you might want to read this document about an unusual step that happen at build time to create a special C header file.

## System Information Discovery

`posix_ipc` needs to know various IPC-related facts about its host system. For instance, some operating systems don't offer a timed wait function for semaphores. This module wants to make that functionality available when it's present, and also needs to know when it's _not_ present and therefore can't be used.

This kind of information needs to be known before `posix_ipc` is compiled. To get that information, `build_support/discover_system_info.py` runs when `setup.py` is invoked. (In `posix_ipc` releases prior to 1.2.0, this script was called `prober.py`.)

The goal of `discover_system_info.py` is to write a C header file called `src/system_info.h`. (In `posix_ipc` releases prior to 1.2.0, this file was called `probe_results.h`.) This header file isn't part of the source distribution, nor should it be. It contains values that are specific to the system on which `posix_ipc` is built.

## The System Info Header File

A sample header file (`system_info.sample.h`) is included in this distribution. It contains all of the possible entries that _could_ be present in the file, along with documentation about each.

In addition to allowing the build process to create this file for you, you can also write your own `src/system_info.h`. **If that file exists when `posix_ipc` is built, the build system will use your version instead of creating its own.** This can be useful if `discover_system_info.py` is failing for some reason, or if you think it's generating the wrong values. It can also help support cross compilation scenarios. (See below.)

If you want to create your own `system_info.h`, copy `system_info.sample.h` to `src/system_info.h`, and edit `src/system_info.h` before you build.

### Cross Compilation

If you want to run `posix_ipc` on a system other than the one where it was built, you'll probably be better off if you create a custom `system_info.h`. In fact, it might be your only option. A couple of scenarios in `discover_system_info.py` need to run small C programs that are compiled on the fly. If your build system can't run the binaries it creates for your target system, `discover_system_info.py` might raise a `DiscoveryError` exception.

### Descriptive, Not Definitive

It's very important to understand that the values in `system_info.h` _describe_ your system to `posix_ipc`. They don't change the behavior of your operating system. For instance, if you arbitrarily change `SEM_VALUE_MAX` in `system_info.h` to a larger number, that won't actually increase the maximum valid value for a semaphore on your system. It will only misinform `posix_ipc` about what your system accepts, and a misinformed `posix_ipc` will probably behave badly.
