# Portable dumb distcc

## Goals

* Support multiple compilers (not just GCC)
  * In particular support cross-compilation with [clang-cl](https://clang.llvm.org/docs/MSVCCompatibility.html)
* Work on common OSes (Linux, Windows, Mac OS X)

## Status

* GCC: supported
* MSVC: supported but requires non-zero setup

## MSVC: supported compilation mode

* A single source file compiled to an object file (as in `/c`)
* PDB generation is not supported, use `/Z7` for debugging info

## Running the daemon

### Windows + msvc

* Install python 3.7 from [python.org](https://www.python.org/downloads/release/python-374).
  Make sure the directory holding the `python.exe` executable is in the `PATH`.
  Note: version of python 3.7 from Windows Store is known to **not** work.

* Run 'Visual Studio 20NN command prompt'

* Start `pdistccd`:

  ```bash
     python .\pdistcc\bin\pdistccd.py --host 0.0.0.0
  ```

Note: by default `pdistccd` listens the loopback interface only.

### Linux

* Install python 3, version 3.6 is known to work
* Install GCC (or clang)
* Start `pdistccd`:

  ```bash
  ./pdistcc/bin/pdistccd.py --host 0.0.0.0
  ```


## Distributed compilation

### Linux

* Install the required compilers and start `pdistccd` or
  [distccd](https://github.com/distcc/distcc) on several machines

* Configure the project

  ```bash
  cmake \
    -DCMAKE_CXX_COMPILER_LAUNCHER=/path/to/pdistcc/bin/pdistcc.py \
    -DCMAKE_C_COMPILER_LAUNCHER=/path/to/pdistcc/bin/pdistcc.py \
    path/to/sources
  ```

* Compile

  ```bash
  export DISTCC_HOSTS="foo:3632/10 bar:3632/10"
  cmake --build . --verbose --parallel 10
  ```

Not very different from [distcc](https://github.com/distcc/distcc)


### Windows + msvc

Note that the way [msbuild](https://docs.microsoft.com/en-us/visualstudio/msbuild/msbuild?view=vs-2019)
builds things makes it extremely difficult to distribute the compilation (and/or cache its results).
[nmake](https://docs.microsoft.com/en-us/cpp/build/reference/nmake-reference?view=vs-2019) is not capable
of running several tasks in parallel. Therefore one needs a proper build tool: [ninja](https://ninja-build.org).

* Install required version of msvc and start `pdistccd` on several machines.
  Double check that all compilation machines use the same msvc version and
  the target architecture.

* Run `Visual Studio 20NN command prompt` (same as on compilation machines)

* Configure the project

  ```bash
  cmake -G"Ninja" ^
    -DCMAKE_CXX_COMPILER_LAUNCHER=python;\path\to\pdistcc\bin\pdistcc.py ^
    -DCMAKE_C_COMPILER_LAUNCHER=python;\path\to\pdistcc\bin\pdistcc.py ^
    -DCMAKE_CXX_FLAGS_RELWITHDEBINFO='/O2 /Z7 /EHs' ^
    -DCMAKE_C_FLAGS_RELWITHDEBINFO='/O2 /Z7' ^
    -DCMAKE_BUILD_TYPE=RelWithDebInfo ^
    path/to/sources
  ```

* Compile

  ```bash
  set DISTCC_HOSTS="foo:3632/10 bar:3632/10"
  cmake --build . --verbose --parallel 10
  ```

## Heterogeneous compilation cluster with [clang](https://clang.llvm.org)

* Install `clang` which supports Windows and Linux targets on every build machine
* Run `pdistccd` on every build machine
* When configuring the project explicitly specify the OS/architecture:

  ```bash
  cmake \
    -DCMAKE_CXX_COMPILER='clang++' \
    -DCMAKE_C_COMPILER='clang' \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_CXX_FLAGS_RELWITHDEBINFO='-O2 -g --target=x86_64-pc-linux-gnu' \
    -DCMAKE_C_FLAGS_RELWITHDEBINFO='-O2 -g --target=x86_64-pc-linux-gnu' \
    -DCMAKE_CXX_COMPILER_LAUNCHER=path/to/pdistcc/bin/pdistcc.py \
    -DCMAKE_C_COMPILER_LAUNCHER=path/to/pdistcc/bin/pdistcc.py \
    path/to/sources
  ```
* Compile as usual:

  ```bash
  export DISTCC_HOSTS='foo:3632/10 bar:3632/10 bigiron:3632/40'
  cmake --build . --verbose --parallel=20
  ```

Note: on Linux machines one can use the standard [distcc](https://github.com/distcc/distcc) as a client.
