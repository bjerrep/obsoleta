# Generators

**obsoleta on the runtime**

Once obsoleta is resolving packages and continuously checks that all versions adds up it would be probably be nice to have just a part of this functionality on the runtime as well. One use case would be when using dynamic link libraries where applications as the first thing during start can verify that the libraries loaded are in fact the intended ones (although it might be less of an issue if the libraries are always referenced by a versioned name). Another use case would be to trivially query the runtime for version information for the used libraries as part of getting general information regarding a running system. The real reason behind the generator concept was of course that it seemed like a fun thing to play with.

Obviously the straightforward solution to the above use cases would be to ship the package json files embedded in the binaries and then just use those with a json parser. This has not been tried yet as the requirement for a json parser somehow didn't sound attractive - for now there is a C generator, with a naive C++ facade for C++, implementing a few operations like check, info, getting the name and getting the version.

Since a generator per definition requires an interpreter or a compiler or something much more wonderful it isn't part of the normal test suite.

Time will tell if its a good idea or not to let obsoleta mess with real source files. Obsoleta normally couldn't care less if it is parts for frying pans or some kind of software modules that exists next to the package files. Also please note that everything on this page is beyond experimental, consider yourself warned.



## C (C++) generator

For a package located in e.g. *local/temp*, generate obsoleta C/C++  source and include files with:

`./dixi.py --path local/temp --generate_c --generate_src src --generate_inc inc`

This will add two .c files to ./src which should be included for building for C and two include files in ./inc which should be added to the include search path. If the package file contains an entry "language": "C++" then there will be added an .cpp file as well. A C++ project will need to include both .c and .cpp files.

Notice that the --generate_c command above should be executed for a package whenever the package file changes since the sourcefiles reflects whats in the package file.

This generator is targeting an environment of mixed C and C++ which makes it slightly messy. There is no native C++ generator yet. The generated code is the first proof of concept so the versions are just verified verbatim, there are no equality (<,>,<= etc) support yet.

The test program *test_c_generator.py* can be used as reference since the above is all the documentation written so far. The test program copies package files and build scripts from *templates/c* into *local/temp*. There are the application **a** that uses the dynamic library **b** which is statically linked with the third and last library **c**.  Next the package directories are updated with auto generated source files as seen above and obsoleta is used to get the build order. After this the respective *build.sh* scripts are called for pure C and *build_cpp.sh* scripts for a mixture of C and C++. Finally the C binary *a/a.out* and the C++ *a/a_cpp* binary is executed, hopefully showing that the runtime versions for the libraries verifies to a pass for both C and C++.

### An example on how to manually generate C source files

Make a temporary directory and populate it with a package file

```
mkdir -p local/temp

./dixi.py --printtemplate > local/temp/obsoleta.json
```

now open the obsoleta json package file and add the line "language": "C" to the package file not to get any C++ wrapper stuff (for no particular reason). Now its time to generate the source files and get a quick overview of the output:

```
./dixi.py --conf testdata/test.conf --path local/temp --generate_c --generate_src src --generate_inc inc

tree local/temp

local/temp
├── inc
│   ├── obsoleta_a.h
│   ├── obsoleta.h
│   └── version.hpp
├── obsoleta.json
└── src
     ├── obsoleta_a.c
     └── obsoleta.c
```

Actually the test program *test_c_generator.py* will make a local/temp that is more interesting since it will among other things contain a main.c and show an example on how to call the files above.

