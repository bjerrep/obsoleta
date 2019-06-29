[![Build Status](https://travis-ci.org/bjerrep/obsoleta.svg?branch=master)](https://travis-ci.org/bjerrep/obsoleta)

# obsoleta

#### <center>A version checking and version resolving framework <BR> for very small development setups </center>

When there is a few developers then everything is fine up to the point where someone suggests to break the big single build up into smaller entities as build and test execution times starts to get excessive. So now you have e.g. executable **a** depending on library **b** depending on library **c**. That's a splendid idea except for the fact that just about every time someone is making breaking changes in **c** everything else is a pain. The CI might get it right every time, but fellow developers keep wasting time trying to figure out what went wrong. Too often someone updates e.g. the **a** repository alone and then have to figure out why stuff stopped working or the build breaks. Obsoleta tries to be a tool that makes it more transparent what is going on.

There are tonnes of modules, packages, whatever in the world that does the same as is done here. Probably the biggest selling point for Obsoleta is that it is very small and hopefully relatively hackable.

There are two scripts in obsoleta, obsoleta.py itself and a helper script called dixi.py and they have a chapter each. The first part below describe working with obsoleta.


## Status

This is a work in progress. The code is riddled with yet to be found subtle and not so subtle bugs and the documentation is this page that probably suffers from a lack of direction and contains information that was never or is no more the truth. But the general idea hopefully burns through. There is a test.py script in the repository - assuming that it actually executes to a pass then its tests can be used as reference.

## The metadata

Getting the trivial stuff out of the way first. From now on the **a**, **b** and **c** from above are all called packages and they will be used as the template for a small setup. A package is identified as a directory hosting a json file *obsoleta.json* containing

- a mandatory and unique name
- a mandatory version number
- an optional track (e.g. "development", "testing", "production")
- an optional arch (free form string e.g. "linux_x86_64", "windows_x86_64" etc)
- an optional buildtype (free form string e.g. "debug" or "release")
- an optional 'depends' list, listing other packages

This is how a obsoleta.json file can look like (generated with dixi.py --printtemplate):

	{
	    "name": "a",
	    "version": "0.0.0",
	    "track": "development",
	    "arch": "archname",
	    "buildtype": "buildtype",
	    "depends": [
		{
		    "name": "b",
		    "version": "0.0.0",
		    "track": "development",
		    "arch": "archname",
		    "buildtype": "buildtype"
		}
	    ]
	}


Wether or not the optional track, arch and buildtype are globally enabled is defined in a configuration file loaded by Obsoleta. Even if they are enabled they are optional in the json files which might be the reason for any small inconsistencies further down this page.

All the meta data for a package can be bundled into a single identifier called compact form, used both internally and for console output. It can look like these:

No optionals enabled:

**name:version**

All optionals enabled but unspecified for a given package (falling back to default values):

**name:anytrack:anyarch:unknown:version**

When everything is in use:

**name:testing:linux_x86_64:release:version**

### Specifying a package

The name given with the --package argument are split with ':' as delimiter to between 1 to 5 elements depending on enabled optionals. The following are all valid package specifications (for what is also called the compact name) when all optionals are enabled:

- "all"
- "*"
- name:track:arch:buildtype:version
- name:track:arch:buildtype
- name:track:arch
- name:track
- name

Its deeply unfair but thats all the explanation there is for now. The examples below uses the last version since they are very simple and the name itself is enough for a unique identification.

## Example

Given one or more root directories Obsoleta recursively scans for *obsoleta.json* files (with a given limit on the number of recursions, see the depth paragraph). The directory name itself is not used by Obsoleta, the package name is always taken from the json file.
So seen from a file system view it could look like this:

	test_simple/
	├── a_master
	│   └── obsoleta.json
	├── b_bugfix
	│   └── obsoleta.json
	└── c_rubbish
	    └── obsoleta.json

The obsoleta.json files for a minimal **a**-**b**-**c** package setup could contain something like this: (truncated for brevity, this is in three separate valid json files)

	  "name": "a", "version": "0.1.2",
		  "depends": [{ "name": "b", "version": "0.1.2"  }]

	  "name": "b", "version": "0.1.2",
		  "depends": [{ "name": "c", "version": "0.1.2"  }]

	  "name": "c", "version": "0.1.2"

## Checking

Assuming the local workspace contains the package json files as above then a --check will find no problems:

	./obsoleta.py --path test/test_simple --package a --check
	checking package "a": success

The tree view will also show errors if there are any (which there isn't):

	/obsoleta.py --path test/test_simple  --package a --tree
	a:anytrack:anyarch:0.1.2
	  b:anytrack:anyarch:0.1.2
	    c:anytrack:anyarch:0.1.2

That was expected. Now someone makes a change in **c**, refreshes the json files with new version numbers and checks in **a**, **b** and **c**.

A colleague checks out **a** to get the latest and greatest. The json files will now contain

	  "name": "a", "version": "0.1.2",
		  "depends": [{ "name": "b", "version": "0.2.2"  }]

	  "name": "b", "version": "0.1.2",
		  "depends": [{ "name": "c", "version": "0.1.2"  }]

	  "name": "c", "version": "0.1.2"

which as might be suspected iznogood:

	./obsoleta.py --path test/test_simple  --package a --check
	checking package "a": failed, 1 errors found
	   Package not found: b:anytrack:anyarch:0.2.2 required by a:anytrack:anyarch:0.1.2

which can be seen in the tree as well

	./obsoleta.py --path test/test_simple  --package a --tree
	a:anytrack:anyarch:0.1.2
	  b:anytrack:anyarch:0.2.2
	       - Package not found: b:anytrack:anyarch:0.2.2 required by a:anytrack:anyarch:0.1.2

which suggests that **b** should be updated. Once that is done it will be a proper **c** that is missing.

## Resolving

It is possible to use comparison operators (> >= == <= <) for any packages listed in the depends sections. Assuming that three versions of **c** are in the filesystem it could look like this:

	  "name": "a", "version": "0.2.2",
		  "depends": [{ "name": "c", "version": "0.>=2.2"  }]

	  "name": "c",  "version": "0.1.2"

  	  "name": "c",  "version": "0.2.2"

  	  "name": "c",  "version": "0.3.2"

where a '--tree a' with some kind of mathematical justice returns

	./obsoleta.py --path test/test_simple2  --package a --tree
	a:anytrack:anyarch:0.1.2
	  c:anytrack:anyarch:0.3.2

## Track, Arch & Buildtype

### Track

The track is used to add release management life cycles into the mix. The allowed tracks are currently arbitrarily hardcoded as a.o. 'anytrack', 'development', 'testing' and 'production'. The catch is that they introduce a binding where pulled in packages need to be at the same track or better than the parent.

	  "name": "a", "version": "0.1.2",
		  "depends": [{ "name": "b", "version": "0.1.2"  }]

	  "name": "b", "track" : "release", "version": "0.1.2"

This is ok, **b** will be picked up:

	/obsoleta.py --path test/test_simple5 --tree a
	a:anytrack:anyarch:0.1.2
	  b:release:anyarch:0.1.2

But this:

	  "name": "a", "track": "testing", "version": "0.1.2",
		  "depends": [{ "name": "b", "version": "0.1.2"  }]

	  "name": "b", "track" : "development", "version": "0.1.2"

is not legal:

	a:test:anyarch:0.1.2
	  b:test:anyarch:0.1.2
	       - Package not found: b:test:anyarch:0.1.2 required by a:test:anyarch:0.1.2

Complaining about the package b:test:anyarch:0.1.2 which is a dummy constructed for the occasion might not be the best way to convey the problem but that's the way it is right now. Also the valid track names are currently hardcoded in the python script which is not the way it should be.

### Arch

The arch (architecture) attribute acts as an appendix to the name so e.g. a library can coexist in multiple flavors for the otherwise same name, version, track and buildtype.

The default arch name is 'anyarch' which as the name suggests matches any architecture. This perhaps unfortunately gives it kind of two different meanings when dealing with packages producing binaries: The first would be that only one architecture is ever used and no packages bother to define an "arch" attibute and everything then just gets 'anyarch'. The other meaning would be in a multi arch setup where a package using 'anyarch' would be a package without binaries, e.g. a tool/utility package or perhaps an include file only package for c/c++.


### Buildtype

Buildtype is ignored except for the track 'production' where it is illegal to mix different buildtypes. This is a somewhat debatable implementation and it might not hold in the real world.

## Search paths

Obsoleta currently have no concept of a default search path and it will fall over if none is given. Search paths can be specified on the command line using '--path' and/or in the configuration file. All paths are concatenated to a single list which is traversed at each invocation (no caching, at least not yet). The configuration file have a 'paths' which is just a json array, and a 'env_paths' string which is shell expanded (it can contain environment variables in $ style). Both '--path' and 'env_paths' can be : separated lists.

## Slots/multislots

Slot and multislots are a way to deal with the fact that once the 'arch' attibute is actually used for different architectures then the straight forward package files used so far on this page won't cut it. 

### Slots

A use case could be that a developer working on multiple architectures decides to check out the same repository once for each architecture. This could lead to the following file structure:

    ├── a_x86/
    │   ├── obsoleta.json
    │   └── obsoleta.key
    └── a_x86_64/
        ├── obsoleta.json
        └── obsoleta.key
    

This will result in the same obsoleta.json file (from the SCM) in multiple directories and obsoleta will complain about duplicate packages.

The current solution is to add a new file alongside obsoleta.json called obsoleta.key defining the so-called slot that the current directory represents. This key file should then -not- be in the SCM. How the key file is made say by a CI that is about to make a clean rebuild should be implemented in the local toolchain. A slotted obsoleta.json and a matching key file could look like

**obsoleta.json**

	{
	  "slot": {
	    "name": "b",
	    "version": "0.1.2"
	  },
	  "key1": {
	    "arch": "x86_64"
	  },
	  "key2": {
	    "version": "0.1.3",
	    "arch": "x86"
	  }
	}

**obsoleta.key**

	{
	  "key": "key2"
	}

What happens is that the package definition used by obsoleta will be the 'slot' dictionary with additions or rewrites from the given slot. From the above this will yield

	{
	    "name": "b",
	    "version": "0.1.3",
	    "arch": "x86"
	}

### Multislots

If building for multiple architectures is done out-of-source in a single directory it could look like this:

    a/
    ├── obsoleta.json
    ├── build_x86/
    │   └── obsoleta.key
    └── build_x86_64/
        └── obsoleta.key

So compared to the slot version above there will now have to be multiple key files, one in each build directory, where all are referring to the same package file. The only difference to the slot section above is that the base key is now called "multislot" rather than just "slot" in the package file.

### Blacklisting and skipping

There are three ways to tell obsoleta to ignore a directory (and any subdirectories) even if there are otherwise valid obsoleta files present.

The simplest one is to add a 'obsoleta.skip' file in any directories that should be ignored.

Alternatively to what might end up as littering skip files throughout the filestructure there is a 'blacklist_paths' entry in the configuration file and a --blacklist_path command line argument. They are joined to one list and are both used.

### Search depth

The default recursive scan depth relative to the specified root directories are 1. It can be changed on the command line with --depth and/or it can be defined in the configuration file with a "depth" entry. A command line depth number overrules any configuration depth number.

## Build support

The examples above are most of all just intellectual exercises until the information can be used for actual building. For this there is a --buildorder option which does pretty much what it says:

	./obsoleta.py --path test/test_simple --package all --buildorder
	c:anytrack:anyarch:0.1.2
	b:anytrack:anyarch:0.1.2
	a:anytrack:anyarch:0.1.2

For automation the paths are more interesting and can be listed using --printpaths:

	./obsoleta.py --path test/test_simple --package all --buildorder --printpaths
	/home/obsoleta/test/test_simple/c
	/home/obsoleta/test/test_simple/b
	/home/obsoleta/test/test_simple/a

Conceptually there isn't a long way to a pseudo script that could wrap everything up:

	for path in "--path test/test_simple --package all --buildorder --printpaths"
		cd path
		git pull
		export obsoleta=$obsoleta:path # for the build system to use
		./build.sh

## dixi

dixi is a utility script intended to make usage easier for both a CI and developers when scripting. The purpose of dixi is that it shouldn't normally be required to edit the json package files manually once they are made and it intends to provide an easy interface for manipulating a package file. Dixi always works on a uniquely specified package file and newer tries to figure out in what contexts the given package is used as opposed to the obsoleta script.

Currently dixi supports the following operations:

	--getversion
	--setversion x.y.z
	--incmajor
	--incminor
	--incbuild
	--getarch
	--setarch arch
	--gettrack
	--settrack track
	--getbuildtype
	--setbuildtype buildtype

Dixi support for slotted packages are so far limited as it only operates on the resolved package. It can figure out that it needs to write in the slot section of a slotted package file but its not clever enough to discover if an entry actually came from a key'ed section. So dixi can work on the version and the track assuming that the values originally were in the slot section. This limited thing is just waiting for a proper implementation for it to dissapear.




