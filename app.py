# coding: utf-8

from flask import Flask, render_template, abort, send_from_directory, request
from gluish.path import iterfiles
from gluish.utils import shellout
import hashlib
import logging
import os
import shelve
import shutil
import tempfile

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
logger = logging.getLogger('pkpy')

app = Flask(__name__)

# CACHE: hashed(package name) -> package file
# PACKAGE_CACHE: the directory the artefacts reside in (subject to QUOTA)
CACHE = os.path.join(app.static_folder, '.cache.shelve')
PACKAGE_CACHE = os.path.join(app.static_folder, '.cache.packages')
PACKAGE_QUOTA = 10000000


@app.before_request
def ensure_package_cache():
    if not os.path.exists(PACKAGE_CACHE):
        os.makedirs(PACKAGE_CACHE)


@app.before_request
def abort_on_overquota(quota=PACKAGE_QUOTA, directory=PACKAGE_CACHE):
    total = 0
    for filename in os.listdir(directory):
        total += os.path.getsize(os.path.join(directory, filename))
    if total > quota:
        logger.error('OVERQUOTA: %s/%s' % (total, quota))
        return abort(503)
    else:
        logger.debug('QUOTA OK: %s/%s' % (total, quota))


@app.errorhandler(404)
def page_not_found(e):
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


@app.route("/q", methods=["POST"])
def build_from_user_input():
    target = request.form.get('target', 'deb')
    if not target in ('deb', 'rpm'):
        return abort(404)
    github_id = request.form.get('ghid')
    username, repo = github_id.split('/', 1)
    try:
        filename = github_clone_and_build(username, repo, target)
    except RuntimeError as err:
        logger.error("Could not find or build %s for %s/%s: %s" % (
                     target, username, repo, err))
        return abort(404)
    return send_from_directory(PACKAGE_CACHE, filename, as_attachment=True,
                               attachment_filename=filename)


@app.route("/github/<username>/<repo>/<target>")
def build_from_github(username, repo, target):
    if not target in ('deb', 'rpm'):
        return abort(404)
    try:
        filename = github_clone_and_build(username, repo, target)
    except RuntimeError as err:
        logger.error("Could not build %s: %s" % (repo_url, err))
        return abort(404)
    return send_from_directory(PACKAGE_CACHE, filename, as_attachment=True,
                               attachment_filename=filename)


@app.route("/pypi/<name>/<target>")
def build_from_pypi(name, target):
    """ Does not cache anything. Serves from static. """
    if not target in ('deb', 'rpm'):
        return abort(404)

    cache_key = hashlib.sha1('%s:%s' % (name, target)).hexdigest()
    cache = shelve.open(CACHE)

    if not cache_key in cache:
        logger.debug('Building %s for %s...' % (target, name))
        stopover = tempfile.mkdtemp(prefix='pkpy-')
        try:
            shellout('cd {stopover} && fpm --verbose -s python -t {target} {name}',
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

    return send_from_directory(PACKAGE_CACHE, filename, as_attachment=True,
                               attachment_filename=filename)

@app.route("/")
def hello():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
