from subprocess import Popen
import urlparse
import sys
import time
import hashlib
try:
    import simplejson as json
except ImportError:
    import json

from pyramid.response import Response
from pyramid.view import view_config
from pyramid.url import resource_url

from sqlalchemy.exc import DBAPIError

from .models import (
    DBSession,
    CheckedLink,
    )

from .utils import invalid_url, API_KEY


@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    try:
        result = DBSession.query(CheckedLink.parentname).distinct().count()
    except DBAPIError:
        return Response(conn_err_msg, content_type='text/plain', status_int=500)
    return {'result': result, 'project': 'liches'}

conn_err_msg = """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to run the "initialize_liches_db" script
    to initialize your database tables.  Check your virtual
    environment's "bin" directory for this script and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""

@view_config(route_name='parenturl', renderer='templates/parenturl.pt')
def parenturl_view(request):
    parenturl = request.params.get('url')
    error = invalid_url(parenturl)
    if error:
        return Response(error, content_type='text/plain', status_int=500)
    urlobj = urlparse.urlparse(parenturl)
    pagename = urlparse.urlunparse([urlobj.scheme, urlobj.netloc, urlobj.path, None, None, None])
    try:
        results = DBSession.query(CheckedLink).filter_by(parentname=parenturl).distinct().all()
    except DBAPIError:
        return Response(conn_err_msg, content_type='text/plain', status_int=500)
    if results is None:
        res = {'num': 0, 'urls': [], 'name': pagename}
    else:
        urls = []
        for url in results:
            urls.append({
                'urlname': url.urlname,
                'parentname': url.parentname,
                'baseref': url.baseref,
                'valid': url.valid,
                'result': url.result,
                'warning': url.warning,
                'info': url.info,
                'url': url.url,
                'line': url.line,
                'col': url.col,
                'name': url.name,
                'checktime': url.checktime,
                'dltime': url.dltime,
                'dlsize': url.dlsize,
                'cached': url.cached,
                'level': url.level,
                'modified': url.modified,})
        res = {'num': len(results), 'urls': urls, 'name':pagename}
    if request.params.get('format') == 'json':
        response =  Response(json.dumps(res))
        response.content_type='application/json'
        return response
    else:
        return res


@view_config(route_name='checkpages', renderer='templates/pages.pt')
def checked_pages_view(request):
    parenturl = request.params.get('url')
    try:
        if parenturl:
            results = DBSession.query(CheckedLink.parentname).filter(CheckedLink.parentname.like(parenturl +'%')).distinct().all()
        else:
            results = DBSession.query(CheckedLink.parentname).distinct().all()
    except DBAPIError:
        return Response(conn_err_msg, content_type='text/plain', status_int=500)
    if results is None:
        res = {'num': 0, 'urls': [], 'name': pagename}
    else:
        urls = []
        for url in results:
            urls.append([url[0],
            resource_url(request.context, request, 'checkurl', query={'url': url[0]})])
        res = {'num': len(results), 'urls': urls, 'name':parenturl}
    if request.params.get('format') == 'json':
        response =  Response(json.dumps(res))
        response.content_type='application/json'
        return response
    else:
        return res

@view_config(route_name='linkcheck', renderer='templates/checklink.pt')
def check_url(request):
    url = request.params.get('url')
    key = request.params.get('key')
    error = invalid_url(url)
    if error:
        return Response(error, content_type='text/plain', status_int=500)
    t = int(time.time()/100)
    valid = False
    for i in range(-1,2):
        if hashlib.md5(str(t+i) +API_KEY + url).hexdigest() == key:
            valid = True
            break
    if valid:
        process = Popen(['bin/checkpage', sys.argv[1], url])
        result = {'status': 'linkcheck initialized', 'name': url}
    else:
        return Response('illegal or missing key', content_type='text/plain', status_int=403)
    if request.params.get('format') == 'json':
        response =  Response(json.dumps(result))
        response.content_type='application/json'
        return response
    else:
        return result
