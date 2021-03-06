#!/usr/bin/env python3.5

import argparse
import math
import os
import random
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
    default_template_dir = "template/"
    default_resource_dir = "res/"

    default_logo_color = "random"
    default_cover_color = "random"
    default_back_color = "contrast"

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--list", "--song-list", dest="song_list", default=default_song_list)
    parser.add_argument("-o", "--output", default=default_output)

    parser.add_argument("-w", "--work", "--work-dir", dest="work_dir", default=default_work_dir)
    parser.add_argument("-s", "--song", "--songs", "--song-dir", "--songs-dir", dest="song_dir", default=default_song_dir)
    parser.add_argument("-t", "--template", "--template-dir", dest="template_dir", default=default_template_dir)
    parser.add_argument("-r", "--res", "--resource", "--resources", "--res-dir", "--resource-dir", "--resources-dir" , dest="resource_dir", default=default_resource_dir)

    parser.add_argument("--logo-color", default=default_logo_color)
    parser.add_argument("--title-color", default=None)
    parser.add_argument("--cover-color", default=default_cover_color)
    parser.add_argument("--back-color", default=default_back_color)

    parser.add_argument("-a", "--authors", default="")

    parser.add_argument("--no-sort", dest="sort", action="store_false")
    parser.add_argument("--tex-file", default=None)
    parser.add_argument("-k", "--keep", action="store_true")
    parser.add_argument("-c", "--chorded", action="store_true")
    parser.add_argument("--developer", action="store_true")

    config = parser.parse_args()

    config.logo_color = parse_color(config.logo_color)
    config.title_color = parse_color(config.title_color, config.logo_color)
    config.cover_color = parse_color(config.cover_color)
    config.back_color = parse_color(config.back_color, suggestion=config.title_color, contrast=config.cover_color)
    print("Logo color:", *config.logo_color)
    if config.title_color != config.logo_color:
        print("Title color:", *config.title_color)
    print("Cover color:", *config.cover_color)
    print("Back color:", *config.back_color)

    if config.tex_file is None:
        config.tex_filename = os.path.basename(config.output).rsplit(".", 1)[0] + ".tex"
        config.tex_file = join(config.work_dir, config.tex_filename)

    if not config.output.endswith(".pdf"):
        config += ".pdf"

    return config

def integrity_check(config):
    if not config.developer:
        result = subprocess.run(["sh", "-c", "cat " + join(config.template_dir, "*") +" | md5sum"], stdout=subprocess.PIPE, universal_newlines=True)
        if result.stdout != "5f62b8505708c8f99a2ffbe105296d46  -\n":
            raise SongbookError("The templates has been modified!!!\nYou shouldn't do that")

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
        return "".join(self.lines)


def parse_color(*colors, suggestion=None, contrast=None):
    color = [color for color in colors if color][0]
    if isinstance(color, tuple):
        return color
    color = color.replace(" ", "")
    if color == "contrast" and contrast is not None:
        contrast_value = (contrast[0] + contrast[1] + contrast[2]) / 3
        distance = math.sqrt((contrast[0] - suggestion[0])**2 + (contrast[1] - suggestion[1])**2 + (contrast[2] - suggestion[2])**2)
        print(distance)
        if distance >= 128:
            return suggestion
        elif contrast_value > 128:
            return (0, 0, 0)
        else:
            return (255, 255, 255)
    elif color == "random":
        red = random.randint(0, 255)
        green = random.randint(0, 255)
        blue = random.randint(0, 255)
    elif color.startswith("#"):
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
    else:
        red, green, blue = (int(x) for x in color.split(","))
    return (red, green, blue)

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

    numbered.sort(key=lambda s: s.number) # Always sort numbered
    if config.sort:
        unnumbered.sort(key=lambda s: s.title)

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

def create_logo(config):

    # color_string = " ".join("{0:.8f}".format(color/255).rstrip("0").rstrip(".") for color in (red, green, blue)) + " rg"
    color_string = "{0:.8f} {1:.8f} {2:.8f} rg".format(*[c/255 for c in config.logo_color])

    eps_name = "logo_template.eps"
    with open(join(config.template_dir, eps_name)) as file:
        eps = file.read()
        eps = eps.replace("1 0 1 rg", color_string)
    final_name = "logo.eps"
    with open(join(config.work_dir, final_name), "w") as file:
        file.write(eps)


def create_texfile(song_tex, config):
    template_name = "template.tex"
    with open(join(config.template_dir, template_name)) as file:
        tex = file.read()

    title_color = "{0},{1},{2}".format(*config.title_color)
    cover_color = "{0},{1},{2}".format(*config.cover_color)
    back_color = "{0},{1},{2}".format(*config.back_color)

    tex = tex.replace("{{BODY}}", song_tex)
    tex = tex.replace("{{TITLECOLOR}}", title_color)
    tex = tex.replace("{{COVERCOLOR}}", cover_color)
    tex = tex.replace("{{BACKCOLOR}}", back_color)

    authors = [author.strip() for author in config.authors.split(",")]
    if len(authors) == 0:
        author_string = "RKG"
    elif len(authors) == 1:
        author_string = str(authors[0])
    else:
        *many, last = authors
        author_string = "{0} \\& {1}".format(", ".join(many), last)
    print(author_string)
    tex = tex.replace("{{AUTHORS}}", author_string)

    with open(config.tex_file, "w") as file:
        file.write(tex)

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
    shutil.copy(join(config.template_dir, "songs.sty"), config.work_dir)
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
    integrity_check(config)
    os.makedirs(os.path.normpath(config.work_dir), exist_ok=True)
    song_files = read_songlist(config.song_list)
    songs = load_songs(song_files)
    categories = categorize(songs)
    sorted_songs = sort_songs(songs)
    hyperlink(sorted_songs, categories)
    create_logo(config)
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
