import os
import shutil
import re

from src import dirsAndFiles

addon_version = "8.20"


def get_file_data(path):
    fin = open(path, "rt")
    data = fin.read()
    fin.close()
    return data


def save_data_to_file(path, data):
    fin = open(path, "wt")
    fin.write(data)
    fin.close()


def update_addon_version(version):
    data = get_file_data(dirsAndFiles.addon_toc_file)
    data = re.sub(r"## Notes: v\d+\.\d+", "## Notes: v" + version, data)
    data = re.sub(r"## Version: \d+\.\d+", "## Version: " + version, data)
    save_data_to_file(dirsAndFiles.addon_toc_file, data)

    data = get_file_data(dirsAndFiles.addon_core_file)
    data = re.sub(r"Bis-Tooltip v\d+\.\d+", "Bis-Tooltip v" + version, data)
    save_data_to_file(dirsAndFiles.addon_core_file, data)
    pass


def create_addon_zip(version):
    shutil.make_archive(
        os.path.join(dirsAndFiles.addon_zip_dir, "Bistooltip-v" + version),
        'zip',
        dirsAndFiles.addon_dir)
    pass


if __name__ == '__main__':
    update_addon_version(addon_version)

    create_addon_zip(addon_version)
