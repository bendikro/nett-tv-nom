#!/usr/bin/env python3
#
# A simple python script to fetch and play video from nrk nett-tv.
#
# Copyright (2012) gspr, bro
# Licensed under the 3-clause BSD license.
#

import argparse
import urllib.request
from html.parser import HTMLParser
import subprocess
import os, sys
import datetime as dt

DEFAGENT="Mozilla/5.0 (iPad; U; CPU OS OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B367 Safari/531.21.10"
DEFPLAYER="vlc"

import lxml.etree as et

class Subtitles(object):

    def __init__(self, input_file_or_url, output_file, encoding):
        if os.path.isfile(input_file_or_url):
            xmltext = open(input_file_or_url).read()
        else:
            opener = urllib.request.build_opener()
            f = opener.open(input_file_or_url)
            xmltext = f.read()
            f.close()

        subtitles = self.xml2srt(xmltext)
        self.write_srt_file(subtitles, output_file, encoding)

    def handle_subtitle_element(self, p, tags):
        children = p.getchildren()
        text = ""

        if p.text and p.text.strip():
            text += p.text.strip()

        for c in children:
            if c.tag == tags["br"]:
                text += "\n"
            elif c.tag == tags["span"]:
                vs = c.values()
                if vs and vs[0] == "italic":
                    text += "<i>%s</i>" % c.text.strip()
            if c.tail and c.tail.strip():
                text += c.tail

        begin = p.get('begin')
        timestamp, seconds = begin[:5], begin[6:] # begin.rsplit(':', 1)
        begin = dt.datetime.strptime(timestamp, '%H:%M') + \
                dt.timedelta(0, 0, float(seconds) * 1e6)
        dur = p.get('dur')
        timestamp, seconds = dur[:5], dur[6:] # dur.rsplit(':', 1)
        dur = dt.datetime.strptime(timestamp, '%H:%M') + \
              dt.timedelta(0, 0, float(seconds) * 1e6)
        dur = dt.timedelta(0, dur.hour,
                (dur.minute*60 + dur.second) * 1e6 + dur.microsecond)
        end = begin + dur
        begin = '%s,%03d' % (begin.strftime('%H:%M:%S'), begin.microsecond//1000)
        end   = '%s,%03d' % (end.strftime('%H:%M:%S'), end.microsecond//1000)
        return ('%s --> %s' % (begin, end), text)

    def write_srt_file(self, subtitles, output_file, encoding):
        fout = open(output_file, "w", encoding=encoding)
        print("Saving subtitle with encoding: %s" % encoding)
        for i, s in enumerate(subtitles):
            fout.write("%d\n" % i)
            fout.write("%s\n" % s[0])
            fout.write("%s\n" % s[1])
            fout.write("\n")
        fout.close()

    def xml2srt(self, xmltext):
        tree = et.fromstring(xmltext)
        namepsace = tree.nsmap[None]
        tags = {}
        tags["br"] = "{%s}br" % namepsace
        tags["span"] = "{%s}span" % namepsace
        body = tree[1]
        div = body[0]
        children = div.getchildren()
        subs = []
        for p in children:
            subs.append(self.handle_subtitle_element(p, tags))
        return subs

def get_available_stream_info(url, user_agent):
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-agent", user_agent)]
    f = opener.open(url)
    data = f.read().decode("utf-8")
    lines = data.splitlines()
    if len(lines[0]) < 10:
        del lines[0]

    streams = []
    while len(lines) >= 2:
        streams.append((lines[0], lines[1]))
        del lines[0]
        del lines[0]
    return streams

def get_which_path(cmd):
    import subprocess
    path = subprocess.check_output(["which", cmd])
    path = path.decode("utf-8").strip()
    if not path.endswith(cmd):
        print("Failed to find the path to %s" % cmd)
        return None
    return path

def print_examples():
    examples = """Examples:

Play stream with default player (vlc)
nrk-nett-tv.py -p http://tv.nrk.no/serie/kveldsnytt/nnfa23070712/07-07-2012

Play stream with mplayer
nrk-nett-tv.py -p mplayer http://tv.nrk.no/serie/kveldsnytt/nnfa23070712/07-07-2012

Fetch subtitles and save as subtitle.srt
nrk-nett-tv.py -s subtitle.srt http://tv.nrk.no/serie/beat-for-beat/muhu16000912/23-11-2012

Fetch subtitles and save as subtitle.srt with utf-8 encoding
nrk-nett-tv.py -s subtitle.srt --sub-encoding utf-8 http://tv.nrk.no/serie/beat-for-beat/muhu16000912/23-11-2012

Play stream, fetch subtitle and show subtitles in mplayer (Arguments after the url are passed directly to the player)
nrk-nett-tv.py -p mplayer -s subtitle.srt http://tv.nrk.no/serie/kveldsnytt/nnfa23070712/07-07-2012 -sub subtitle.srt

Save stream to file (requires vlc/cvlc)
nrk-nett-tv.py -o stream-output-file http://tv.nrk.no/serie/kveldsnytt/nnfa23070712/07-07-2012

Play and save stream to file simultaneously (requires vlc)
nrk-nett-tv.py -p -o stream-output-file http://tv.nrk.no/serie/kveldsnytt/nnfa23070712/07-07-2012
"""

    print(examples)

class Parser(HTMLParser):
    src = ""
    def handle_starttag(self, tag, attrs):
        if tag == "div":
            for attr,val in attrs:
                if attr == "data-media":
                    self.src = val
                if attr == "data-subtitlesurl":
                    self.subs = val

def main():
    argparser = argparse.ArgumentParser(description="Extract video stream from NRK Nett-TV", add_help=False)
    argparser.add_argument("-o", "--output-file",  help="Save stream to disk with vlc.", required=False)
    argparser.add_argument("-p", "--player", nargs='?',
                           help="Play the stream. Default player: %s" % DEFPLAYER,
                           required=False, const=DEFPLAYER, default=DEFPLAYER)
    argparser.add_argument("-l", "--list-streams", action='store_true',
                           help="Show the available streams.", required=False)
    argparser.add_argument("-s", "--subtitle-file", help="Fetch subtitle and save to file.",
                           default="latin1", required=False)
    argparser.add_argument("-se", "--subtitle-encoding", help="Save subtitle with the specified encoding.",
                           required=False)
    argparser.add_argument("-vs", "--video-stream", help="With -p, use this video stream. [4]",
                           required=False, default=4)
    argparser.add_argument("url", help="URL to parse")
    argparser.add_argument("-u", "--user-agent", help="Send this user-agent header. Defaults to [%s]" % DEFAGENT,
                           required=False, default=DEFAGENT)
    argparser.add_argument("-e", "--echo", action='store_true',
                           help="Echo stream URL and exit instead of playing.", required=False)
    argparser.add_argument("--examples", action='store_true', help="Print examples.", required=False)
    argparser.add_argument("-v", "--verbose", action='store_true', help="Be verbose.", required=False)
    argparser.add_argument("-h", "--help", action='store_true', help="Show usage.", required=False)
    argparser.add_argument('args_to_forward',
                           help='Remaining arguments after the url are passed to the invoked program.',
                           nargs=argparse.REMAINDER)
    args = argparser.parse_args()

    if args.help:
        argparser.print_help()
        exit()
    elif args.examples:
        print_examples()
        exit()

    opener = urllib.request.build_opener()
    opener.addheaders = [("User-agent", args.user_agent)]
    f = opener.open(args.url)
    parser = Parser()
    parser.feed(f.read().decode("utf-8"))
    f.close()

    if parser.src == "":
        print("Unable to extract stream URL.")
        exit(1)

    if args.echo:
        print("Manifest  url:", parser.src)
        if hasattr(parser, "subs"):
            print("Subtitles url: %s%s" % (args.url, parser.subs))
        else:
            print("No subtitles found.")
        exit(0)
    elif args.list_streams:
        print("\nAvailable streams:")
        streams = get_available_stream_info(parser.src, args.user_agent)
        for i, s in enumerate(streams):
            print("Stream %d: %s\nUrl:%s\n" % (i, s[0], s[1]))
        if hasattr(parser, "subs"):
            print("Subtitles url: %s%s" % (args.url, parser.subs))
        exit(0)
    elif args.subtitle_file:
        if hasattr(parser, "subs"):
            subs_url = "http://tv.nrk.no%s" % parser.subs
            sub = Subtitles(subs_url, args.subtitle_file, args.subtitle_encoding)
        else:
            print("No subtitles available.")
    if args.output_file or args.player:
        streams = get_available_stream_info(parser.src, args.user_agent)
        if int(args.video_stream) >= len(streams):
            print("Invalid video stream index: %d" % args.video_stream)
            exit(0)
        arglist = []
        executable = None
        # This must be done with vlc
        if args.output_file and args.player:
            executable = get_which_path("vlc")
            arglist.append("--sout")
            arglist.append("#duplicate{dst=display,dst=std{access=file,mux=raw,dst=%s}}" % args.output_file)
        # This must be done with vlc
        elif args.output_file:
            executable = get_which_path("cvlc")
            if not executable:
                executable = get_which_path("vlc")
            arglist.append("--sout")
            arglist.append("file/raw:%s" % args.output_file)
        # This can be with any player
        else:
            executable = get_which_path(args.player)

        if args.args_to_forward:
            arglist.extend(args.args_to_forward)

        cmd = [executable]
        cmd.extend(arglist)
        cmd.append(streams[int(args.video_stream)][1])

        if args.verbose:
            print("Executing command:", cmd)
        p = subprocess.Popen(cmd)
        ret = p.wait()
        exit(ret)
    else:
        print(parser.src)
        exit(0)
    exit(0)

if __name__ == "__main__":
    main()
