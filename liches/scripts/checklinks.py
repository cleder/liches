import csv
import subprocess
import string
import random
import os
import sys
import transaction

from sqlalchemy import engine_from_config

from ..utils import invalid_url, linkchecker_options

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from ..models import (
    DBSession,
    CheckedLink,
    LinkCheck,
    Base,
    CSV_HEADER,
    )


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [linkcheckid] \n'
           'linkcheckid is optional, when given only the linkcheck with this id will be executed',
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    lc_id = None
    if len(argv) == 3:
        try:
            lc_id = int(argv[2])
        except:
            usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    if lc_id is None:
        linkchecks = DBSession.query(LinkCheck).filter_by(active=True).all()
    else:
        linkchecks = DBSession.query(LinkCheck).filter_by(check_id=lc_id).all()
    for linkcheck in linkchecks:
        filename = ''.join(random.sample(
            string.ascii_letters + string.digits, 16)) + '.csv'
        options = linkchecker_options(linkcheck)
        options.append("--file-output=csv/utf-8/" + filename)
        options.append(linkcheck.url)
        subprocess.call(options)
        with transaction.manager:
            DBSession.query(CheckedLink).filter(
                CheckedLink.parentname.like(linkcheck.root_url +'%')).delete(
                synchronize_session=False)
            DBSession.expire_all()
            fo = open(filename, 'rU')
            reader=csv.reader(fo, delimiter=';')
            line = reader.next()
            #the first lines are comments and are to be ignored
            while line[0].startswith('#'):
                line = reader.next()
            #the header comes after the comments
            #linkchecker < 8 does not have 'modified' field
            assert(line[:16] == CSV_HEADER[:16])
            try:
                for line in reader:
                    if line[0].startswith('#'):
                        continue
                    else:
                        line = [v.decode('UTF-8') for v in line]
                    checked_link = CheckedLink( *line)
                    DBSession.add(checked_link)
            except:
                print "Error in line: ", line
        os.remove(filename)
