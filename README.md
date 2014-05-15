README
======

Turn your python code into native packages and ship faster.

Works with all packages on pypi. Works with many
open source projects hosted on Github and Bitbucket.

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

Option 3: Create a separate package, something like pkpy. Install
pkpy on the deployment machine. Then give pkpy a unique
identifier (e.g. URL), and pkpy will fetch the zip (Option 1),
extract and install it on its own.

Option 4: ...

Getting started
---------------

    $ git clone https://github.com/miku/pkpy.git
    $ cd pkpy
    $ mkvirtualenv pkpy
    $ pip install -r requirements
    $ python app.py
    2014-05-15 12:19:18,982 INFO  * Running on http://0.0.0.0:5000/
    2014-05-15 12:19:18,982 INFO  * Restarting with reloader
    ....

From another terminal:

    # create package from pypi
    $ wget "localhost:5000/pypi/elasticsearch/deb"
    ...
    ... - 'python-elasticsearch_1.0.0_all.deb' saved [76828/76828]

    # create package from pypi with C bindings
    $ wget "localhost:5000/pypi/numpy/rpm"
    ...
    ... - 'python-numpy-1.8.1-1.x86_64.rpm' saved [4203449/4203449]

    # create package from github
    $ wget "localhost:5000/github/miku/gluish/rpm"
    ...
    ... - 'python-gluish-0.1.36-1.noarch.rpm' saved [44049/44049]


Screenie
--------

First screenshot, built by a small [pre-commit hook](https://gist.github.com/miku/111bb2c029ffe89475d7).

![Screenshot](http://i.imgur.com/ubCMsdU.png)
