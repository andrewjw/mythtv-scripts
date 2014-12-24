#!/usr/bin/env python
#
# Creates symlinks to mythtv recordings using more-human-readable filenames.
# See --help for instructions.
#
# Automatically detects database settings from config.xml, and loads
# the mythtv recording directory from the database.

from MythTV import MythDB, findfile, Job
from optparse import OptionParser
import os

#def rename_all():
#    for rec in Recorded.getAllEntries():
#        

def link_all():
    db = MythDB()
    channels = get_channels(db)
    if opts.live:
        recs = db.searchRecorded(livetv=True)
    else:
        recs = db.searchRecorded()
    targets = {}
    for rec in recs:
        details = get_link_details(rec, channels)
        if details is None:
             continue
        source, dest, destfile = details
        if dest not in targets:
             targets[dest] = {}
        targets[dest][destfile] = source

    for (path, dirs, files) in os.walk(opts.dest, topdown=False):
        dir = path.split("/")[-1]
        if dir == "":
            continue
        if dir not in targets:
            for fname in files:
	    	if not os.path.islink(path + "/" + fname):
                    raise Exception("Found non link - " + path + "/" + fname)
                os.unlink(path + "/" + fname)
            os.rmdir(path)
            continue
        else:
            for fname in files:
                print dir, fname
                if dir not in targets or fname not in targets[dir]:
                    if not os.path.islink(path + "/" + fname):
                        raise Exception("Found non link - " + path + "/" + fname)
                    os.unlink(path + "/" + fname)
                else:
                    del targets[dir][fname]
                    print targets[dir]
                    if len(targets[dir]) == 0:
                        del targets[dir]
    for dir in targets:
        if not os.path.exists(opts.dest + dir):
            os.mkdir(opts.dest + dir)
        for fname in targets[dir]:
            os.symlink(targets[dir][fname], opts.dest + "/" + dir + "/" + fname)

def get_link_details(rec, channels):
    sg = findfile(rec.basename, rec.storagegroup, rec._db)
    if sg is None:
        return
    source = os.path.join(sg.dirname, rec.basename)
    target = rec.formatPath(format)
    target = target.replace(u"\xa3", "")
    for cid in channels:
        target = target.replace("(%i)" % (cid, ), "(%s)" % (channels[cid], ))
    return source, target.split("/")[0], target.split("/")[1]

def get_channels(db):
    c = db.db.cursor()
    c.execute("select chanid, name from channel")
    r = {}
    for (id, name) in c:
        r[id] = name
    return r

def gen_link(rec):
    sg = findfile(rec.basename, rec.storagegroup, rec._db)
    source = os.path.join(sg.dirname, rec.basename)
    dest = os.path.join(opts.dest, rec.formatPath(format))
    if opts.underscores:
        dest = dest.replace(' ','_')
    sdest = dest.split('/')
    for i in range(2,len(sdest)):
        tmppath = os.path.join(*sdest[:i])
        if not os.access(tmppath, os.F_OK):
            os.mkdir(tmppath)
    os.symlink(source, dest)

parser = OptionParser(usage="usage: %prog [options] [jobid]")

parser.add_option("--dest", action="store", type="str", dest="dest",
        help="""Specify the directory for the links.  If no pathname is given, links
                will be created in the show_names directory inside of the current 
                MythTV data directory on this machine.

                WARNING: ALL symlinks within the destination directory and its
                subdirectories (recursive) will be removed.""")
parser.add_option("--jobid", action="store", type="int", dest="jobid",
        help="""Create a link only for the specified recording file.  This argument
                may be used with an automated user-job run on completion of a recording.""")
parser.add_option("--chanid", action="store", type="int", dest="chanid",
        help="""Create a link only for the specified recording file.  This argument
                must be used in combination with --starttime.  This argument may be used
                in a custom user-job, or through the event-driven notification system's
                "Recording Started" event.""")
parser.add_option("--starttime", action="store", type="int", dest="starttime",
        help="""Create a link only for the specified recording file.  This argument
                must be used in combination with --chanid.  This argument may be used
                in a custom user-job, or through the event-driven notification system's
                "Recording Started" event.""")
parser.add_option("--filename", action="store", type="str", dest="filename",
        help="""Create a link only for the specified recording file.  This argument may
                be used in a custom user-job, or through the event-driven notification
                system's "Recording Started" event.""")
parser.add_option("--live", action="store_true", default=False, dest="live",
        help="""Specify that LiveTV recordings are to be linked as well.  Default is to
                only process links for scheduled recordings.""")
parser.add_option("--format", action="store", dest="format",
        help="""Specify the output format to be used to generate link paths.""")
parser.add_option("--underscores", action="store", dest="underscores",
        help="""Replace whitespace in filenames with underscore characters.""")
parser.add_option('-v', '--verbose', action='store', type='string', dest='verbose',
        help='Verbosity level')

opts, args = parser.parse_args()

if opts.dest is None:
    opts.dest = '/mnt/nfs/mythtv/plex/'
if opts.format is None:
    format = '%T/%T - %pY%-%pm%-%pd %ph:%pi:%ps - %S (%c)'
if opts.jobid:
    db = MythDB()
    job = Job(opts.jobid, db=db)
    rec = Recorded((job.chanid, job.starttime), db=db)
    gen_link(rec)
elif opts.chanid and opts.starttime:
    rec = Recorded((opts.chanid, opts.starttime))
    gen_link(rec)
elif opts.filename:
    db = MythDB()
    rec = db.searchRecorded(basename=opts.filename)
    gen_link(rec)
else:
    link_all()

