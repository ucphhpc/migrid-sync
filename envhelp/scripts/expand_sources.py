#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# which - wrapper to locate a binary respecting python interpreter information
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---

"""Download any required self-distributing packages."""

import glob
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

SCRIPT_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
STAGING_DIR = os.path.join(ROOT_DIR, "envhelp", "staging")
SOURCE_URL_BASE = "https://github.com/ucphhpc"

PACKAGE_REPOS_TO_BRANCH = {
    "migux": {
        "repository": "migrid-ux",
        "repository_rev": "7f3e19feac33c246d5a778f7bb74f9dce9aa28bb",
    }
}


def download_url(url, output_file, use_wget=False):
    if use_wget:
        download_url_wget(url, output_file)
    else:
        urllib.request.urlretrieve(url, output_file)


def download_url_wget(url, output_file):
    subprocess.run(["wget", "-O", output_file, url], stderr=subprocess.DEVNULL)


def main(argv):
    use_wget = "--use-wget" in argv

    # start with an entirely clean state
    shutil.rmtree(STAGING_DIR, ignore_errors=True)

    # make the package directory
    os.makedirs(STAGING_DIR)

    # make the temporary download directory
    staging_dir = os.path.join(STAGING_DIR, ".download")
    os.mkdir(staging_dir)

    for package_name, package_dict in PACKAGE_REPOS_TO_BRANCH.items():
        package_repo = package_dict["repository"]
        commit_id = package_dict["repository_rev"]
        package_repo_with_branch = "%s-%s" % (package_repo, commit_id)

        package_dir_staging = os.path.join(
            staging_dir, package_repo_with_branch
        )
        downloaded_archive_file = os.path.join(
            staging_dir, "_%s.zip" % (package_repo,)
        )

        # grab an archive containing installable package files
        package_url = os.path.join(
            SOURCE_URL_BASE,
            package_repo,
            "archive",
            "%s.zip" % (commit_id,),
        )
        download_url(package_url, downloaded_archive_file, use_wget=use_wget)

        # extract it
        archive = zipfile.ZipFile(downloaded_archive_file)
        archive.extractall(staging_dir)

        # find the raw package files
        packages_glob = os.path.join(
            package_dir_staging, "dist/%s-*" % (package_name,)
        )
        packages_paths = glob.glob(packages_glob)

        # copy the raw package files into a common packages directory
        for package_path in packages_paths:
            package_file_name = os.path.basename(package_path)
            target_path_path = os.path.join(STAGING_DIR, package_file_name)
            shutil.copyfile(package_path, target_path_path)

        # remove all staged files
        shutil.rmtree(staging_dir)

    packages_list = os.path.join(STAGING_DIR, ".packages.lst")

    # write a listing of the available package files alongside them
    with open(packages_list, "w") as outfile:
        package_names_only = [
            file_name
            for file_name in os.listdir(STAGING_DIR)
            if not file_name.startswith(".")
        ]
        package_names_only.sort()
        print(*package_names_only, sep="\n", file=outfile)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
