#!/usr/bin/env python3

import argparse
import urllib.request
from html.parser import HTMLParser
import subprocess

DEFAGENT="Mozilla/5.0 (iPad; U; CPU OS OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B367 Safari/531.21.10"
DEFPLAYER="/usr/bin/ffplay"

def main():
    argparser = argparse.ArgumentParser(description="Extract video stream from NRK Nett-TV")
    argparser.add_argument("-p", "--play", help="Start playing stream with this ffplay-compatible player. If omitted, simply print stream URL.", required=False)
    argparser.add_argument("-v", "--video-stream", help="With --play, use this video stream.", required=False, default=8)
    argparser.add_argument("-a", "--audio-stream", help="With --play, use this audio stream.", required=False, default=7)
    argparser.add_argument("url", help="URL to parse")
    argparser.add_argument("-u", "--user-agent", help="Send this user-agent header.", required=False, default=DEFAGENT)
    args = argparser.parse_args()

    opener = urllib.request.build_opener()
    opener.addheaders = [("User-agent", args.user_agent)]
    f = opener.open(args.url)

    parser = Parser()
    parser.feed(f.read().decode("utf-8"))
    
    f.close()

    if parser.src == "":
        sys.stderr.write("Unable to extract stream URL.\n")
        exit(1)

    if args.play:
        print("Launching ffplay-compatible player %s." %(args.play))
        p = subprocess.Popen([args.play, "-vst", str(args.video_stream), "-ast", str(args.audio_stream), parser.src])
        ret = p.wait()
        exit(ret)
    else:
        print(parser.src)
        exit(0)

    exit(0)

class Parser(HTMLParser):
    src = ""
    def handle_starttag(self, tag, attrs):
        if tag == "video":
            for attr,val in attrs:
                if attr == "src":
                    self.src = val
                    break
    
if __name__ == "__main__":
    main()
