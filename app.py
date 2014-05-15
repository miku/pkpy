# coding: utf-8

from flask import Flask, render_template, redirect, url_for, abort, send_from_directory, request
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
CACHE = os.path.join(app.static_folder, '.cache.shelve')


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
        dst = os.path.join(app.static_folder, basename)
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
    github_id = request.form.get('ghid')
    username, repo = github_id.split('/', 1)
    try:
        filename = github_clone_and_build(username, repo, 'deb')
    except RuntimeError as err:
        logger.error("Could not build %s" % repo_url)
        return abort(404)
    return send_from_directory(app.static_folder, filename, as_attachment=True,
                               attachment_filename=filename)


@app.route("/github/<username>/<repo>/<target>")
def build_from_github(username, repo, target):
    if not target in ('deb', 'rpm'):
        return abort(404)
    try:
        filename = github_clone_and_build(username, repo, target)
    except RuntimeError as err:
        logger.error("Could not build %s" % repo_url)
        return abort(404)
    return send_from_directory(app.static_folder, filename, as_attachment=True,
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
            dst = os.path.join(app.static_folder, basename)
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

    return send_from_directory(app.static_folder, filename, as_attachment=True,
                               attachment_filename=filename)

@app.route("/")
def hello():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
