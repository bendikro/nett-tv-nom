#!/usr/bin/env python
#
# A simple python script to fetch and play video from nrk nett-tv.
#
# Copyright (2012-2016) gspr, bro
# Licensed under the 3-clause BSD license.
#

from __future__ import print_function

import argparse
import datetime as dt
import json
import os
import subprocess
import re
import time


try:
    from termcolor import cprint
except:
    cprint = print

try:
    from urllib import request
    from html.parser import HTMLParser
    from urllib.parse import unquote, urljoin
except:
    # Python 2.7
    import urllib2 as request
    from urlparse import urljoin
    from urllib import unquote
    from HTMLParser import HTMLParser


DEFAGENT = "Mozilla/5.0 (iPad; U; CPU OS OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10"\
           "(KHTML, like Gecko) Version/4.0.4 Mobile/7B367 Safari/531.21.10"
DEFPLAYER = "vlc"
DEFAULT_STREAM = -1
VLC_PATH = ""

__version__ = "1.0.4"


class Subtitles(object):
    """Parse and save subtitles"""

    def __init__(self, input_file_or_url, output_file, encoding):
        if os.path.isfile(input_file_or_url):
            xmltext = open(input_file_or_url).read()
        else:
            opener = request.build_opener()
            f = opener.open(input_file_or_url)
            xmltext = f.read()
            f.close()

        self.output_file = output_file
        self.encoding = encoding
        self.subtitles = self.xml2srt(xmltext)

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
        timestamp, seconds = begin[:5], begin[6:]  # begin.rsplit(':', 1)
        begin = dt.datetime.strptime(timestamp, '%H:%M') + dt.timedelta(0, 0, float(seconds) * 1e6)
        dur = p.get('dur')
        timestamp, seconds = dur[:5], dur[6:]  # dur.rsplit(':', 1)
        dur = dt.datetime.strptime(timestamp, '%H:%M') + dt.timedelta(0, 0, float(seconds) * 1e6)
        dur = dt.timedelta(0, dur.hour,
                           (dur.minute * 60 + dur.second) * 1e6 + dur.microsecond)
        end = begin + dur
        begin = '%s,%03d' % (begin.strftime('%H:%M:%S'), begin.microsecond // 1000)
        end = '%s,%03d' % (end.strftime('%H:%M:%S'), end.microsecond // 1000)
        return ('%s --> %s' % (begin, end), text)

    def save(self):
        self.write_srt_file(self.subtitles, self.output_file, self.encoding)

    def write_srt_file(self, subtitles, output_file, encoding):
        import codecs
        with codecs.open(output_file, "w", encoding="utf-8") as fout:
            for i, s in enumerate(subtitles):
                try:
                    fout.write("%d\n" % i)
                    fout.write("%s\n" % s[0])
                    fout.write("%s\n" % s[1])
                    fout.write("\n")
                except (Exception) as e:
                    print("Failed to write to file: '%s. Error:'" % s[1], e)

    def xml2srt(self, xmltext):
        import lxml.etree as et
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


def read_url(url, user_agent):
    opener = request.build_opener()
    opener.addheaders = [("User-agent", user_agent)]
    f = opener.open(url)
    data = f.read().decode("utf-8")
    return data


def get_available_stream_info(url, args):
    if args.verbose > 2:
        print("Fetching manifest from:", url)

    manifest_data = read_url(url, args.user_agent)
    lines = manifest_data.splitlines()
    streams = []
    stream_url_base = os.path.dirname(url) + "/"

    if args.verbose > 1:
        print("Stream base URL: '%s'" % stream_url_base)

    i = 0
    while i < len(lines):
        if not lines[i].startswith("#"):
            stream_url = lines[i]
            if not stream_url.startswith("http"):
                stream_url = urljoin(stream_url_base, lines[i])
            streams.append((lines[i - 1], stream_url))
            i += 1
        i += 1
    return streams


def get_which_path(cmd):
    if os.name == "nt":
        return VLC_PATH

    import subprocess
    path = subprocess.check_output(["which", cmd])
    path = path.decode("utf-8").strip()
    if not path.endswith(cmd):
        if os.path.isfile(VLC_PATH) and os.access(VLC_PATH, os.X_OK):
            return VLC_PATH
        print("Failed to find the path to %s" % cmd)
        return None
    return path


def print_examples():
    examples = """Examples:

Play stream with default player (vlc)
nrk-nett-tv.py http://tv.nrk.no/serie/kveldsnytt/nnfa23070712/07-07-2012

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

    def __init__(self):
        HTMLParser.__init__(self)
        self.src = ""
        self.manifests = []
        self.episodes = []
        self.possible_episodes = []
        self.season_link = None
        self.subs = None
        self.tag_level = []
        self.base_url = None
        self.programid = None

    @property
    def mediaelement(self):
        return "https://psapi-we.nrk.no/mediaelement/%s" % self.programid

    def handle_starttag(self, tag, attrs):
        self.tag_level.append((tag, attrs))
        if tag == "div":
            for attr, val in attrs:
                if attr == "data-media":
                    self.src = val
                if attr == "data-subtitlesurl":
                    self.subs = val

        if tag == "a":
            attrs_dict = dict(attrs)
            if "class" in attrs_dict and "p-link" in attrs_dict["class"]:
                # Most probably an episode link
                if attrs_dict["href"].startswith("/serie"):
                    self.possible_episodes.append({"link": attrs_dict["href"], "attrs": attrs_dict})

                if self.tag_level[-2][0] == "li":
                    li_attrs_dict = dict(self.tag_level[-2][1])
                    if ("class" in li_attrs_dict and "episode-item" in li_attrs_dict["class"]
                       and "data-episode" in li_attrs_dict):
                        self.episodes.append({"link": attrs_dict["href"], "attrs": li_attrs_dict})

        if tag == "a":
            for attr, val in attrs:
                if attr == "data-argument":
                    cprint("FOUND data-argument: %s" % val, "green")
                    self.manifests.append(val)

        if tag == "meta":
            attrs_dict = dict(attrs)
            if attrs_dict.get("name", None) == 'programid':
                self.programid = attrs_dict["content"]

            if attrs_dict.get("name", None) and attrs_dict.get('content', None) == 'episode':
                self.type = "episode"

            if attrs_dict.get("property", None) == 'og:url':
                # Should look like "http://tv.nrk.no/serie/mammon"
                self.base_url = attrs_dict["content"]
                self.season_link = self.base_url

    def handle_endtag(self, tag):
        if not self.tag_level[-1][0] == tag:
            print("last tag does not match end tag:", self.tag_level[-1])
        self.tag_level.pop()


def print_stream(streams, verbose=False):
    for i, s in enumerate(streams):
        print("Stream %d: %s" % (i, s[0]))
        if verbose:
            print("%s\n" % (s[1]))


class VLCOutput(object):

    def __init__(self, outfile):
        self.outfile = open(outfile, "w")

    def close(self):
        self.outfile.close()

    def fileno(self):
        return self.outfile.fileno()


def process_streams(stream_list, args, parts):
    indexes = range(len(stream_list))
    for i in indexes:
        process_stream(stream_list, i, args)


def process_stream(stream_list, index, args):
    if args.verbose > 1:
        print("Processing stream:", stream_list[index])

    streams = get_available_stream_info(stream_list[index]["manifest_url"], args)

    # The stream quality
    if int(args.stream_index) >= len(streams):
        print("Invalid stream index: %s" % args.stream_index)
        exit(0)
    elif args.stream_index == -1:
        # Find the best quality video stream
        max_width = 0
        for i, s in enumerate(streams):
            m = re.match(".*RESOLUTION=(?P<width>\d+)x(?P<height>\d+).*", s[0])
            if m:
                width = int(m.groupdict()["width"])
                if max_width < width:
                    args.stream_index = i
                    max_width = width

    arglist = []
    executable = None
    # This must be done with vlc
    if args.output_file:
        output_file = args.output_file
        # if len(streams) > 1:
        #     output_file += "_%d" % index
        # output_file += ".mkv"
        output_file = "%s%s" % (stream_list[index]["title"], stream_list[index]["title_postfix"])
        if not output_file.endswith(".mkv"):
            output_file += ".mkv"
        if args.verbose > 0:
            print("Output file:", output_file)

        display_option = ""
        executable = get_which_path("vlc")
        if args.verbose > 2:
            print("args.player:", args.player)
        if not args.player:
            display_option = "{novideo,noaudio}"
            cvlc = get_which_path("cvlc")
            if cvlc:
                executable = cvlc

        # If not displaying stream, this is faster than
        # #duplicate, but this doesn't work on live streams.
        if not args.player and not args.live:
            arglist.append("--sout")
            arglist.append("file/mkv:%s" % output_file)
        else:
            arglist.append("--sout")
            arglist.append("#duplicate{dst=display%s,dst=std{access=file,mux=mkv,dst=%s}}" %
                           (display_option, output_file))
    # This can be with any player
    else:
        executable = get_which_path(args.player)

    if args.args_to_forward:
        arglist.extend(args.args_to_forward)

    cmd = [executable]
    cmd.extend(arglist)

    if args.verbose > 2:
        for i, s in enumerate(streams):
            print("Stream(%s): %s" % ("*" if int(args.stream_index) == i else " ", str(s)))
    cmd.append(streams[int(args.stream_index)][1])

    # Make vlc close when finished
    if os.path.basename(executable).startswith("vlc") or \
            os.path.basename(executable).startswith("cvlc"):
        cmd.append("vlc://quit")
        pass

    stderr = subprocess.STDOUT
    if not args.verbose_vlc:
        stderr = VLCOutput("vlc.log" if len(streams) == 1 else "vlc_%d.log" % index)

    if args.verbose > 0 or args.simulate:
        print("Executing command:", cmd)
        if args.simulate:
            return

    # Is not verbose, redirect vlc output to log file
    p = subprocess.Popen(cmd, stderr=stderr)
    while True:
        ret = p.poll()
        if ret is not None:
            if args.verbose > 0:
                print("\nChild has terminated with return value:", ret)
            break
        if args.output_file:
            if os.path.isfile(output_file):
                size = os.stat(output_file).st_size
                print("\rDownloaded %d" % size, end="")
        time.sleep(1)

page_content_count = 0

def parse_url(url, args):
    global page_content_count
    page_data = read_url(url, args.user_agent)
    parser = Parser()
    parser.feed(page_data)

    if args.debug:
        page_content_count += 1
        page_content_filename = "page_content_%d.html" % page_content_count
        print("Writing page content to %s" % page_content_filename)
        with open(page_content_filename, 'wb') as html_output:
            html_output.write(page_data.encode('utf-8'))

    if not parser.programid:
        # This may be live TV
        parser.programid =  os.path.basename(parser.base_url)
        if args.debug:
            print("mediaelement attribute not found. Presume live stream and get programid from base_url: %s" % parser.programid)

    programid = read_url(parser.mediaelement, args.user_agent)
    json_data = json.loads(programid)
    # Url to the manifest file
    parser.src = json_data["mediaUrl"]
    parser.subs = json_data["mediaAssets"][0].get("timedTextSubtitlesUrl", None)
    if parser.subs:
        parser.subs = unquote(parser.subs)

    if args.debug:
        with open("media_%d.json" % page_content_count, 'w') as json_output:
            json_output.write(str(json_data))

        # Season page doesn't have src
        if parser.src:
            manifest_data = read_url(parser.src, args.user_agent)
            manifest_output = open("manifest_%d.m3u8" % page_content_count, "wb")
            manifest_output.write(manifest_data.encode('utf-8'))
            manifest_output.close()
    return parser


def get_stream_list(parser, args):
    stream_list = []

    for m in parser.manifests:
        stream_list.append(m)

    if not stream_list:
        if args.verbose > 2:
            print("This url has only one part")
        if parser.src:
            stream_list.append(parser.src)
    elif args.verbose > 2:
        print("This url has multiple parts (%d)" % len(stream_list))
    return stream_list


def handle_media(parser, args):
    season_parser = None
    episode_parsers = []
    streams_list = []

    if args.list_episodes or args.episodes or args.all:
        episode_links = None
        if parser.season_link:
            season_url = parser.season_link
            if args.debug:
                print("Season link:", repr(season_url))
            season_parser = parse_url(season_url, args)
            episode_links = list(reversed(season_parser.episodes))
            # print("Episodes!:", season_parser.episodes)
            # http://tv.nrk.no/serie/mammon
            # print("base_url:", season_parser.base_url)
            for i, ep_data in enumerate(episode_links):
                # print("ATTRS:", ep_data["attrs"])
                if season_parser.base_url and "data-episode" in ep_data["attrs"]:
                    ep_url = season_parser.base_url + "/" + ep_data["attrs"]["data-episode"]
                    # print("EPURL:", ep_url)
                # print("LINK:", ep_data["link"])
                import urllib.parse
                ep_link = urllib.parse.urljoin(season_parser.base_url, ep_data["link"])
                if ep_url not in ep_link:
                    print("Links are differing: '%s', '%s'" % (ep_url, ep_link))
                e_parser = None
                try:
                    e_parser = parse_url(ep_url, args)
                except urllib.error.HTTPError as e:
                    print("Failed to parse link '%s'" % ep_url)
                if not e_parser:
                    try:
                        e_parser = parse_url(ep_link, args)
                    except urllib.error.HTTPError as e:
                        print("Failed to parse link '%s'" % ep_url)
                        print("Failed to find a valid episode link!")
                        continue
                episode_parsers.append(e_parser)
                # stream_list = get_stream_list(ep, args)

        if not (season_parser or episode_links):
            print("No episodes found!")
        else:
            for i, e in enumerate(episode_links):
                print("Episode %2d - %s" % (i, e["link"]))

    episodes_to_process = []

    if args.list_episodes:
        exit(0)

    # Find episodes
    if args.all or args.episodes:
        if args.all and args.episodes:
            print("Option --all and episodes cannot be specifed together")
            exit(0)

        episodes_to_process = []
        if args.episodes:
            try:
                episodes_to_process = [int(e) for e in args.episodes.split(",")]
            except Exception as e:
                print("Invalid episode index:", e)
        else:
            episodes_to_process = [e for e in range(len(episode_parsers))]

        for e in episodes_to_process:
            stream_list = get_stream_list(episode_parsers[e], args)
            if not stream_list:
                continue
#            cprint("Adding to streams_list: %s" % stream_list, "blue")
            streams_list.append({"title": args.output_file,
                                 "title_postfix": "_episode_%d" % (e + 1),
                                 "manifest_url": stream_list[0],
                                 "subtitle": episode_parsers[e].subs})
        if not streams_list:
            print("This page has no episodes.")
            exit(0)

    if not streams_list:
        stream_list = get_stream_list(parser, args)

        # Has multiple parts
        if len(stream_list) > 1:
            parts = []
            # Part(s) is specified
            if args.parts:
                if args.episodes or args.all:
                    print("Parts cannot be specified together and episodes or --all.")
                    exit(0)
                try:
                    parts = [int(e) for e in args.parts.split(",")]
                except:
                    print("Invalid part index:", args.parts)
            # Use all parts
            else:
                parts = len(stream_list)

            for p in len(parts):
                cprint("Adding to streams_list: %s" % stream_list, "blue")
                streams_list.append({"title": args.output_file,
                                     "title_postfix": "_part_%d" % p,
                                     "manifest_url": stream_list[0],
                                     "subtitle": parser.subs})
        else:
            if args.parts:
                print("The provided url only has one part")
            streams_list.append({"title": args.output_file,
                                 "title_postfix": "",
                                 "manifest_url": stream_list[0],
                                 "subtitle": parser.subs})
    if not streams_list:
        print("No streams found")
        print("parser.src:", parser.src)
        exit(0)

    if args.stream_info:
        print("\nStream info (%s)\n" % args.url)

#        # This page has multiple parts
#        if len(streams_list) > 1:
#            print("Parts:")

        for s in streams_list:
            print("Manifest: ", s["manifest_url"])
            stream_info = get_available_stream_info(s["manifest_url"], args)
            print_stream(stream_info, verbose=True)
            if s["subtitle"]:
                print("Subtitles: %s%s" % (args.url, s["subtitle"]))
            else:
                print("No subtitles found.")

    if args.list_streams:
        print("\nAvailable streams:")
        for i, s in enumerate(streams_list):
            if len(streams_list) > 1:
                print("Part %d:" % (i + 1))
            streams = get_available_stream_info(s["manifest_url"], args)
            print_stream(streams)

    if args.subtitle_file:
        subs_found = False
        for s in streams_list:
            if s["subtitle"]:
                subs_found = True
                subs_url = s["subtitle"]
                sub_filename = "%s%s" % (args.subtitle_file, s["title_postfix"])
                if not sub_filename.endswith(".srt"):
                    sub_filename += ".srt"

                sub = Subtitles(subs_url, sub_filename, args.subtitle_encoding)
                sub.save()
                if args.verbose:
                    print("Subtitle fetched from %s and saved to %s" %
                          (subs_url, sub_filename))
        if not subs_found:
            print("No subtitles available.")

    if args.output_file or args.player:
        process_streams(streams_list, args, episodes_to_process)


def main():
    argparser = argparse.ArgumentParser(description="Extract video stream from NRK Nett-TV")
    argparser.add_argument('--version', action='version', version='%(prog)s: ' + str(__version__))
    argparser.add_argument("-of", "--output-file", help="Save stream to disk with vlc.", required=False)
    argparser.add_argument("-od", "--output-dir", required=False,
                           help="Execute in this directory. Created if non-existent.")
    argparser.add_argument("-p", "--player", nargs='?',
                           help="Play the stream with the specified player. Default player: %s" % DEFPLAYER,
                           required=False, const=DEFPLAYER)
    argparser.add_argument("-ls", "--list-streams", action='store_true',
                           help="Show list of available streams.", required=False)
    argparser.add_argument("-s", "--stream-info", action='store_true',
                           help="Show info about this streams.", required=False)
    argparser.add_argument("-sf", "--subtitle-file", help="Fetch subtitle and save to file.",
                           required=False)
    argparser.add_argument("-se", "--subtitle-encoding", help="Save subtitle with the specified encoding.",
                           default="latin1", required=False)
    argparser.add_argument("-si", "--stream-index", required=False, default=DEFAULT_STREAM,
                           help="With -p, use this stream. Default:[%d]" % DEFAULT_STREAM)
    argparser.add_argument("-ep", "--episodes", help="The episodes to play", required=False)
    argparser.add_argument("-pa", "--parts", help="The parts to play", required=False)
    argparser.add_argument("-a", "--all", action='store_true', help="Process all parts and episodes",
                           required=False)
    argparser.add_argument("-le", "--list-episodes", help="List the available episodes.",
                           action='store_true', required=False)
    argparser.add_argument("--live", action='store_true', required=False,
                           help="This is a live stream. Changes how the stream is saved to file.")
    argparser.add_argument("-u", "--user-agent", required=False, default=DEFAGENT,
                           help="Send this user-agent header. Defaults to [%s]" % DEFAGENT)
    argparser.add_argument("-db", "--debug", action='store_true',
                           help="Debug mode saves the retrieved file to disk.", required=False)
    argparser.add_argument("--examples", action='store_true', help="Print examples.", required=False)
    argparser.add_argument("-v", "--verbose", action='count', default=0, required=False,
                           help="Be verbose. Can be applied multiple times (Max 3)")
    argparser.add_argument("--verbose-vlc", action='store_true', required=False,
                           help="Print vlc output instead of redirecting to log file.")
    argparser.add_argument("-sim", "--simulate", action='store_true', help="Only simulate the download.",
                           required=False)
    argparser.add_argument("url", help="URL to parse")
    argparser.add_argument('args_to_forward',
                           help='Remaining arguments after the url are passed to the invoked program.',
                           nargs=argparse.REMAINDER)
    args = argparser.parse_args()

    if args.examples:
        print_examples()
        exit(0)

    # No option arguments provided, use player as default
    if not (args.stream_info or args.list_streams or args.subtitle_file
            or args.output_file or args.player or args.list_episodes):
        args.player = DEFPLAYER

    # Change to this directory
    if args.output_dir:
        if os.path.isfile(args.output_dir):
            print("Output directory is a file: '%s':" % args.output_dir)
            exit(0)
        else:
            if not os.path.isdir(args.output_dir):
                print("Creating dir")
                os.makedirs(args.output_dir)
            os.chdir(args.output_dir)
        if args.verbose:
            print("Changed working directory to '%s'" % args.output_dir)

    parser = parse_url(args.url, args)

    if parser.src == "":
        print("Unable to extract stream URL.")
        exit(1)

    handle_media(parser, args)
    exit(0)

if __name__ == "__main__":
    main()
