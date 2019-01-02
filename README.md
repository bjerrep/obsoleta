
# obsoleta

#### <center>A version checking and version resolving framework <BR> for very small development setups </center>

When there is a few developers then everything is fine up to the point where someone suggests to break the big single build up into smaller entities as build and test execution times starts to get excessive. So now you have e.g. executable **a** depending on library **b** depending on library **c**. That's a splendid idea except for the fact that just about every time someone is making breaking changes in **c** everything else is a pain. The CI might get it right every time, but fellow developers keep wasting time trying to figure out what went wrong. Too often someone updates e.g. the **a** repository alone and then have to figure out why stuff stopped working or the build breaks. Obsoleta tries to be a tool that makes it more transparent what is going on.

There are tonnes of modules, packages, whatever in the world that does the same as is done here. Probably the biggest selling point for Obsoleta is that it is very small and hopefully relatively hackable. 


## Status

This is a work in progress. The code is riddled with yet to be found subtle and not so subtle bugs and the documentation is this page that probably suffers from a lack of direction and contains information that was never or is no more the truth. But the general idea hopefully burns through. 

## The metadata

Getting the trivial stuff out of the way first. From now on the **a**, **b** and **c** from above are all called packages and they will be used as the template for a small setup. A package is identified as a directory hosting a json file *obsoleta.json* containing

- a mandatory and unique name
- a mandatory version number
- an optional track (e.g. "development", "testing", "production")
- an optional arch (free form string e.g. "linux_x86_64", "windows_x86_64" etc)
- an optional buildtype (free form string e.g. "debug" or "release")
- an optional 'depends' list, listing other packages

Wether or not the optional track, arch and buildtype are globally enabled is defined in a configuration file loaded by Obsoleta. Even if they are enabled they are optional in the json files which might be the reason for any small inconsistencies further down this page. All the meta data are bundled into a single identifier for each package, used both internally and for console output. It can look like these:

No optionals enabled:
**name:version**
	
All optionals enabled but unspecified for a given package (falling back to default values):
**name:anytrack:anyarch:unknown:version**
	
When everything is in use:
**name:testing:linux_x86_64:release:version**

Given one or more root directories Obsoleta recursively scans for *obsoleta.json* files (currently in max two directory levels). The directory name itself is not used by Obsoleta, the package name is always taken from the json file.
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

	./obsoleta --path test/test_simple --check a
	checking package "a": success
	
The tree view will also show errors if there are any (which there isn't):

	/obsoleta.py --path test/test_simple --tree a
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

	./obsoleta.py --path test/test_simple/ --check a
	checking package "a": failed, 1 errors found
	   Package not found: b:anytrack:anyarch:0.2.2 required by a:anytrack:anyarch:0.1.2
   
which can be seen in the tree as well

	./obsoleta.py --path test/test_simple/ --tree a
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

	./obsoleta.py --path test/test_simple2 --tree a
	a:anytrack:anyarch:0.1.2
	  c:anytrack:anyarch:0.3.2

## Track and Arch

### Track

The track is used to add release management life cycles into the mix. The allowed tracks are currently arbitrarily hardcoded as 'anytrack', 'devel', 'test' and 'release'. The catch is that they introduce a binding where pulled in packages need to be at the same track or better than the parent.

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

The arch attribute acts as an appendix to the name so e.g. a library can coexist in multiple flavors for the otherwise same name, version, track and buildtype.

### Buildtype

Buildtype is ignored except for the track 'production' where it is illegal to mix different buildtypes. This is a somewhat debatable implementation and it might not hold in the real world.

## Search paths

Obsoleta currently have no concept of a default search path and it will fall over if none is given. Search paths can be specified on the command line using '--path' and/or in the configuration file. All paths are concatenated to a single list which is traversed at each invocation (no caching, at least not yet). The configuration file have a 'paths' which is just a json array, and a 'env_paths' string which is shell expanded (it can contain environment variables in $ style). Both '--path' and 'env_paths' can be : separated lists.

## Build support

The examples above are most of all just intellectual exercises until the information can be used for actual building. For this there is a --buildorder option which does pretty much what it says:

	./obsoleta.py --path test/test_simple --buildorder all
	c:anytrack:anyarch:0.1.2
	b:anytrack:anyarch:0.1.2
	a:anytrack:anyarch:0.1.2

For automation the paths are more interesting and can be listed using --printpaths:

	./obsoleta.py --path test/test_simple --buildorder all --printpaths
	/home/obsoleta/test/test_simple/c
	/home/obsoleta/test/test_simple/b
	/home/obsoleta/test/test_simple/a

This is as far as this project has made it for now. But conceptually there isn't a long way to a pseudo script that could wrap everything up:

	for path in "--path test/test_simple --buildorder all --printpaths"
		cd path
		git pull
		export obsoleta=$obsoleta:path # for the build system to use
		./build.sh

The start of a utility script intended to make usage easier for both a CI and developers can be found as dixi.py. The purpose of such a script is that it shouldn't normally be required to edit the json files manually once they are made. A developer might use "--increase_minor" and a CI might use'--increase_build' or '--promote a:development:1.2.3 testing'. Stuff like that. The script does nothing yet.


