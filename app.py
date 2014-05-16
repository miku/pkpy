# coding: utf-8

"""
PKPY python packager app.
"""

# pylint: disable=F0401
from flask import Flask, render_template, abort, send_from_directory, request
from gluish.path import iterfiles
from gluish.utils import shellout
import hashlib
import logging
import os
import shelve
import shutil
import tempfile

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger('pkpy')

app = Flask(__name__)

# CACHE: hashed(package name) -> package file
# PACKAGE_CACHE: the directory the artefacts reside in (subject to QUOTA)
CACHE = os.path.join(app.static_folder, '.cache.shelve')
PACKAGE_CACHE = os.path.join(app.static_folder, '.cache.packages')
PACKAGE_QUOTA = 10000000


@app.before_request
def ensure_package_cache():
    """ Make sure the package cache directory exists. """
    if not os.path.exists(PACKAGE_CACHE):
        os.makedirs(PACKAGE_CACHE)


@app.before_request
def abort_on_overquota(quota=PACKAGE_QUOTA, directory=PACKAGE_CACHE):
    """ Abort with 503 as soon the PACKAGE_CACHE exceeds QUOTA. """
    total = 0
    for filename in os.listdir(directory):
        total += os.path.getsize(os.path.join(directory, filename))
    ratio = (float(total) / quota) * 100
    if total > quota:
        logger.error('OVERQUOTA: %s/%s (%0.2f%%)' % (total, quota, ratio))
        return abort(503)
    else:
        logger.debug('QUOTA OK: %s/%s (%0.2f%%)' % (total, quota, ratio))


@app.errorhandler(404)
def page_not_found(e):
    """ 404. """
    return render_template('404.html'), 404


def github_clone_and_build(username, repo, target='deb'):
    """ Clone a repo (username, repo) and build the `target` package.
    Returns the filename, that is placed directly under `static`. """
    repo_url = 'git@github.com:%s/%s.git' % (username, repo)

    cache_key = hashlib.sha1('%s:%s' % (repo_url, target)).hexdigest()
    cache = shelve.open(CACHE)

    if not cache_key in cache:
        logger.debug('Building (%s, %s) ...' % (repo_url, target))
        stopover = tempfile.mkdtemp(prefix='pkpy-')
        shellout("""
            cd {stopover} && git clone {repo_url} &&
            cd {repo} && fpm --verbose -s python -t {target} .""",
                 stopover=stopover, repo_url=repo_url, repo=repo, target=target)
        src = iterfiles(stopover, fun=lambda fn: fn.endswith(target)).next()
        basename = os.path.basename(src)
        dst = os.path.join(PACKAGE_CACHE, basename)
        shellout('cp {src} {dst}', src=src, dst=dst)
        shutil.rmtree(stopover)
        cache[cache_key] = basename
    else:
        logger.debug('Cache hit...')
    filename = cache[cache_key]
    cache.close()
    return filename


def pypi_build(name, target='deb'):
    """ Take a package name and return the filename of the target. """
    cache_key = hashlib.sha1('%s:%s' % (name, target)).hexdigest()
    cache = shelve.open(CACHE)

    if not cache_key in cache:
        logger.debug('Building %s for %s...' % (target, name))
        stopover = tempfile.mkdtemp(prefix='pkpy-')
        try:
            shellout("""cd {stopover} && 
                        fpm --verbose -s python -t {target} {name}""",
                     stopover=stopover, name=name, target=target)
            src = iterfiles(stopover).next()
            basename = os.path.basename(src)
            dst = os.path.join(PACKAGE_CACHE, basename)
            shellout('cp {src} {dst}', src=src, dst=dst)
            shutil.rmtree(stopover)
            cache[cache_key] = basename
        except RuntimeError as err:
            logger.error(err)
            return abort(404)
    else:
        logger.debug('Cache hit...')

    filename = cache[cache_key]
    cache.close()
    return filename


@app.route("/q", methods=["POST"])
def build_from_user_input():
    """ Handles user input. E.g. username/repo
    TODO: allow to give just package names, which are resolved
    over pypi. """
    target = request.form.get('target', 'deb')
    if not target in ('deb', 'rpm'):
        return abort(404)
    name = request.form.get('package')
    if name.count('/') == 1:
        username, repo = name.split('/', 1)
        try:
            filename = github_clone_and_build(username, repo, target)
        except RuntimeError as err:
            logger.error("Fail: %s/%s (%s): %s" % (username, repo, target, err))
            return abort(404)
    elif name.count('/') == 0:
        try:
            filename = pypi_build(name, target=target)
        except RuntimeError as err:
            logger.error('Fail: %s from %s via pypi: %s' % (target, name, err))
            return abort(404)
    else:
        return abort(404)
    return send_from_directory(PACKAGE_CACHE, filename, as_attachment=True,
                               attachment_filename=filename)


@app.route("/github/<username>/<repo>/<target>")
def build_from_github(username, repo, target):
    """ Create download from github username, repo and target. """
    if not target in ('deb', 'rpm'):
        return abort(404)
    try:
        filename = github_clone_and_build(username, repo, target)
    except RuntimeError as err:
        logger.error("Fail: %s/%s: %s" % (username, repo, err))
        return abort(404)
    return send_from_directory(PACKAGE_CACHE, filename, as_attachment=True,
                               attachment_filename=filename)


@app.route("/pypi/<name>/<target>")
def build_from_pypi(name, target):
    """ Does not cache anything. Serves from static. """
    if not target in ('deb', 'rpm'):
        return abort(404)
    try:
        filename = pypi_build(name, target=target)
    except RuntimeError as err:
        logger.error('Fail: %s from %s via pypi: %s' % (target, name, err))
        abort(404)
    return send_from_directory(PACKAGE_CACHE, filename, as_attachment=True,
                               attachment_filename=filename)

@app.route("/")
def hello():
    """ Index. """
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
