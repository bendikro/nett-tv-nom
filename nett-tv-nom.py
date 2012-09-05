#!/usr/bin/env python3

#
# The new NRK Nett-TV provides high-quality web TV without using Flash
# on platforms deemed "supported" [1]. Presently (July 2012), this
# does not include Firefox on GNU/Linux, which gets served a
# Flash-based player instead.
#
# This little program sends an appropriate user agent header (grabbed
# from [1]) to Nett-TV and parses the reply to obtain the URL of a
# video stream that can be used with any player that supports HLS. By
# supplying the name of an ffplay/avplay-compatible executable after
# the --play switch, it can also directly launch this player. You may
# want to tweak the stream numbers.
#
# Example:
# nett-tv-nom.py -p ffplay -a 7 -v 8 http://tv.nrk.no/serie/kveldsnytt/nnfa23070712/07-07-2012
#
# TODO:
# - Add autodetection of various audio/video qualities.
#
# Copyright (2012) gspr
# Licensed under the 3-clause BSD license.
#
# I am not in any way affiliated with NRK. Use of NRK Nett-TV is subject to
# NRK's terms of service. [2]
#
# [1] http://nrkbeta.no/2012/04/23/test-nrks-splitter-nye-nett-tv/
# [2] http://tv.nrk.no/
#

import argparse
import urllib.request
from html.parser import HTMLParser
import subprocess

DEFAGENT="Mozilla/5.0 (iPad; U; CPU OS OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B367 Safari/531.21.10"
DEFPLAYER="/usr/bin/ffplay"

def main():
    argparser = argparse.ArgumentParser(description="Extract video stream from NRK Nett-TV")
    argparser.add_argument("-p", "--player", help="Start playing stream with this ffplay-compatible player. Ignored when using -e. [%s]" %(DEFPLAYER), required=False, default=DEFPLAYER)
    argparser.add_argument("-v", "--video-stream", help="With --play, use this video stream. [8]", required=False, default=8)
    argparser.add_argument("-a", "--audio-stream", help="With --play, use this audio stream. [7]", required=False, default=7)
    argparser.add_argument("url", help="URL to parse")
    argparser.add_argument("-u", "--user-agent", help="Send this user-agent header. [%s]" %DEFAGENT, required=False, default=DEFAGENT)
    argparser.add_argument("-e", "--echo", action='store_true', help="Echo stream URL and exit instead of playing.", required=False)
    args = argparser.parse_args()

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
        print(parser.src)
        exit(0)
    elif args.player:
        print("Launching ffplay-compatible player %s." %(args.player))
        p = subprocess.Popen([args.player, "-vst", str(args.video_stream), "-ast", str(args.audio_stream), parser.src])
        ret = p.wait()
        exit(ret)
    else:
        print(parser.src)
        exit(0)

    exit(0)

class Parser(HTMLParser):
    src = ""
    def handle_starttag(self, tag, attrs):
        if tag == "div":
            for attr,val in attrs:
                if attr == "data-media":
                    self.src = val
                    break
    
if __name__ == "__main__":
    main()
