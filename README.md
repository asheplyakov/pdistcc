# Portable dumb distcc client

## Goals

* Support multiple compilers (not just GCC)
  * In particular support cross-compilation with [clang-cl](https://clang.llvm.org/docs/MSVCCompatibility.html)
* Work on common OSes (Linux, Windows, Mac OS X)

## Status

Sleepless night code dump. **Please don't use it yet**

* GCC: supported
* MSVC: local preprocessing and remote compilation with clang-cl

## MSVC: supported compilation mode

* A single source file compiled to an object file (as in `/c`)
* PDB generation is not supported, use `/Z7` for debugging info
