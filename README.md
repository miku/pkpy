README
======

Turn your python code into native packages and ship faster.

Works with all packages on pypi. Works with open source projects
hosted on Github and Bitbucket.

Acts as an DEB/RPM repository. Add these package repositories
to your system one and start installing python packages
just like native packages. Boom.


Problem
-------

You have a bunch of python packages for a project and you would like
to install them natively via package manager, e.g. rpm.

All you have is a `requirements.txt`. You send your `requirements.txt`
to a service and the service responds.

Option 1: A zip file containing all native packages plus an install
schcript, that will install the packages **in the right order**.
Download the zip to your deployment machine, extract and run `./install`
as root. Done. Pro: No custom repository needed.

Option 2: Set up some package repository.

Option 3: Create a separate package, something like borg. Install
borg on the deployment machine. Then give borg a unique
identifier (e.g. URL), and borg will fetch the zip (Option 1),
extract and install it on its own.


