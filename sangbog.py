#!/usr/bin/env python3.5

import argparse
import os
import re
import shutil
import subprocess
import sys
from os.path import join

class SongbookError(Exception):
    pass

def get_config():
    default_song_list = "songlist.txt"
    default_output = "sangbog.pdf"
    default_work_dir = "work/"
    default_song_dir = "songs/"
    default_tex_dir = "tex/"
    default_resource_dir = "res/"

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--list", "--song-list", dest="song_list", default=default_song_list)
    parser.add_argument("-o", "--output", default=default_output)

    parser.add_argument("-w", "--work", "--work-dir", dest="work_dir", default=default_work_dir)
    parser.add_argument("-s", "--song", "--songs", "--song-dir", "--songs-dir", dest="song_dir", default=default_song_dir)
    parser.add_argument("-t", "--tex", "--tex-dir", dest="tex_dir", default=default_tex_dir)
    parser.add_argument("-r", "--res", "--resource", "--resources", "--res-dir", "--resource-dir", "--resources-dir" , dest="resource_dir", default=default_resource_dir)

    parser.add_argument("--tex-file", default=None)
    parser.add_argument("-k", "--keep", action="store_true")
    parser.add_argument("-c", "--chorded", action="store_true")

    config = parser.parse_args()
    if config.tex_file is None:
        config.tex_filename = os.path.basename(config.output).rsplit(".", 1)[0] + ".tex"
        config.tex_file = join(config.work_dir, config.tex_filename)

    if not config.output.endswith(".pdf"):
        config += ".pdf"

    return config


class Song():
    def __init__(self, filename):
        self.title = None
        self.categories = []
        self.number = None

        self.lines = []
        with open(filename) as file:
            for line in file:
                self.lines.append(line)

                title = re.search("\\beginsong{([^}])}", line)
                if title:
                    self.title = title.group(1)

                category = re.search("\\category{([^}]*)}", line)
                if category:
                    self.categories.append(category.group(1))

                number = re.search("\\songnumber{([^}]*)}", line)
                if number:
                    self.number = number.group(1)

        if self.title is None:
            self.title = os.path.basename(filename)

    def to_tex(self):
        return "\n".join(self.lines)

def read_songlist(song_list):
    with open(song_list) as f:
        song_files = f.read().split("\n")
    song_files = (x.strip() for x in song_files)
    song_files = (x for x in song_files if not x.startswith("#"))
    song_files = (x for x in song_files if not x == "")
    return song_files

def load_songs(song_files):
    return [Song(join(config.song_dir, filename)) for filename in song_files]

def categorize(songs):
    categories = dict()
    for song in songs:
        for category in song.categories:
            entries = categories.get(category, [])
            entries.append(song)
            categories[category] = entries
    return categories

def sort_songs(songs):
    unnumbered = []
    numbered = []
    for song in songs:
        if song.number is None:
            unnumbered.append(song)
        else:
            numbered.append(song)
    unnumbered.sort(key=lambda s: s.title)
    numbered.sort(key=lambda s: s.number)

    sorted_songs = []
    for i in range(0, len(songs)):
        if numbered and i > numbered[0].number:
            raise Exception("Multiple songs try to force the same number")
        elif numbered and i == numbered[0].number:
            sorted_songs.append(numbered.pop(0))
        else:
            sorted_songs.append(unnumbered.pop(0))
    return sorted_songs

def hyperlink(songs, categories):
    pass

def create_song_tex(songs):
    texts = (song.to_tex() for song in songs)
    text = "\n\n%%%%%%%%\n\n".join(texts)
    return text

def create_texfile(song_tex, config):
    header_name = "header.tex"
    frontpage_name = "frontpage.tex"
    backpage_name = "backpage.tex"
    footer_name = "footer.tex"
    with open(join(config.tex_dir, header_name)) as file:
        header = file.read()
    with open(join(config.tex_dir, frontpage_name)) as file:
        frontpage = file.read()
    with open(join(config.tex_dir, backpage_name)) as file:
        backpage = file.read()
    with open(join(config.tex_dir, footer_name)) as file:
        footer = file.read()

    os.makedirs(os.path.normpath(config.work_dir), exist_ok=True)
    with open(config.tex_file, "w") as tex:
        tex.write(header)
        tex.write(frontpage)
        tex.write(song_tex)
        tex.write(backpage)
        tex.write(footer)

def pdflatex(config, capture=True):
    if capture:
        output = subprocess.PIPE
    else:
        output = None

    command = ["pdflatex",
               "-halt-on-error",
               "-file-line-error",
               # "-interaction=\"nonstopmode\"",
               # "-output-directory=\"" + config.work_dir + "\"",
               config.tex_filename]

    # print(" ".join(command))
    result = subprocess.run(command, cwd=config.work_dir, stdout=output, stderr=subprocess.STDOUT, universal_newlines=True)
    if result.returncode != 0:
        if result.stdout is not None:
            print(result.stdout)
        raise SongbookError("pdflatex failed to compile the texfile")

def compile(config):
    pdflatex(config)
    pdflatex(config)
    pdflatex(config)

def move_to_destination(config):
    dir = os.path.normpath(os.path.dirname(config.output))
    os.makedirs(dir, exist_ok=True)
    pdf = config.tex_file[:-len(".tex")] + ".pdf"
    os.replace(pdf, config.output)
    print("Created", config.output)

def clean(config):
    if config.keep:
        return
    shutil.rmtree(config.work_dir)

def main(config):
        song_files = read_songlist(config.song_list)
        songs = load_songs(song_files)
        categories = categorize(songs)
        sorted_songs = sort_songs(songs)
        hyperlink(sorted_songs, categories)
        song_tex = create_song_tex(sorted_songs)
        create_texfile(song_tex, config)
        compile(config)
        move_to_destination(config)
        clean(config)

if __name__ == "__main__":
    config = get_config()
    try:
        main(config)
        sys.exit()
    except SongbookError as e:
        print("ERROR:", str(e))
    except FileNotFoundError as e:
        print("ERROR: Could not find the file '{}'".format(e.filename))
    sys.exit(-1)
