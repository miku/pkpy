# coding: utf-8

from flask import Flask, render_template, redirect, url_for, abort, send_from_directory
from gluish.path import iterfiles
from gluish.utils import shellout
import logging
import os
import shelve
import tempfile

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
logger = logging.getLogger('borghq')

app = Flask(__name__)
CACHE = os.path.join(app.static_folder, '.cache.shelve')


@app.route("/github/<username>/<repo>/<target>")
def build_from_github(username, repo, target):
    if not target in ('deb', 'rpm'):
        return abort(404)
    repo_url = 'git@github.com:%s/%s.git' % (username, repo)

    cache_key = '%s %s' % (repo_url, target)
    cache = shelve.open(CACHE)

    if not cache_key in cache:
        logger.debug('Building (%s, %s) ...' % (repo_url, target))
        stopover = tempfile.mkdtemp(prefix='borghq')
        shellout("""
            cd {stopover} && git clone {repo_url} &&
            cd {repo} && fpm --verbose -s python -t {target} .""",
                 stopover=stopover, repo_url=repo_url, repo=repo, target=target)
        src = iterfiles(stopover, fun=lambda fn: fn.endswith(target)).next()
        basename = os.path.basename(src)
        dst = os.path.join(app.static_folder, basename)
        shellout('cp {src} {dst}', src=src, dst=dst)
        cache[cache_key] = basename
    else:
        logger.debug('Cache hit...')

    filename = cache[cache_key]
    cache.close()

    return send_from_directory(app.static_folder, filename, as_attachment=True,
                               attachment_filename=filename)


@app.route("/pypi/<name>/<target>")
def build_from_pypi(name, target):
    """ Does not cache anything. Serves from static. """
    if not target in ('deb', 'rpm'):
        return abort(404)

    cache_key = '%s %s' % (name, target)
    cache = shelve.open(CACHE)

    if not cache_key in cache:
        logger.debug(   'Building %s for %s...' % (target, name))
        stopover = tempfile.mkdtemp(prefix='pypack')
        shellout('cd {stopover} && fpm --verbose -s python -t {target} {name}',
                 stopover=stopover, name=name, target=target)
        src = iterfiles(stopover).next()
        basename = os.path.basename(src)
        dst = os.path.join(app.static_folder, basename)
        shellout('cp {src} {dst}', src=src, dst=dst)
        cache[cache_key] = basename
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
