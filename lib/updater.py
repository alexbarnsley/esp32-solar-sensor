# Heavily based on https://github.com/rdehuyss/micropython-ota-updater/blob/master/app/ota_updater.py

import json
import os
import gc
import urequests as requests

from lib.config import Config
from lib.logger import Logger

logger = Logger()

def install_update_if_available(config: Config) -> bool:
    """This method will immediately install the latest version if out-of-date.

    This method expects an active internet connection and allows you to decide yourself
    if you want to install the latest version. It is necessary to run it directly after boot
    (for memory reasons) and you need to restart the microcontroller if a new version is found.

    Returns
    -------
        bool: true if a new version is available, false otherwise
    """

    github_repo = config.update_github_repo
    github_src_dir = config.update_github_src_dir
    new_version_dir = config.update_new_version_dir
    api_token = config.update_api_token

    if config.debug:
        logger.set_debug(True)

    _download_config_file(config)

    github_repo = github_repo.rstrip('/').replace('https://github.com/', '')
    github_src_dir = '/' if len(github_src_dir) < 1 else github_src_dir.rstrip('/') + '/'

    (current_version, latest_version) = _check_for_new_version(github_repo)
    if latest_version > current_version:
        logger.output(f'New version found - {latest_version}...')

        _rmtree(modulepath(new_version_dir))

        _create_new_version_file(latest_version, new_version_dir)
        _download_new_version(latest_version, github_src_dir, new_version_dir, github_repo, api_token)
        _install_new_version(new_version_dir)

        gc.collect()

        return True

    gc.collect()

    return False

def _headers(api_token: str | None = None) -> dict[str, str]:
    headers = {
        'User-Agent': 'esp32-solar-sensor-updater',
    }

    if api_token is not None:
        headers['Authorization'] = f'Bearer {api_token}'

    return headers

def _check_for_new_version(github_repo='alexbarnsley/esp32-solar-sensor', api_token: str | None = None):
    current_version = get_version('/')
    latest_version = get_latest_version(github_repo, api_token)

    logger.output('Checking version... ')
    logger.output('\tCurrent version: ', current_version)
    logger.output('\tLatest version: ', latest_version)

    return (current_version, latest_version)

def _create_new_version_file(latest_version, new_version_dir='next'):
    mkdir(modulepath(new_version_dir))

    with open(modulepath(new_version_dir + '/VERSION.txt'), 'w') as versionfile:
        versionfile.write(latest_version)
        versionfile.close()

    logger.output(f'Created VERSION.txt with {latest_version}')

def _download_config_file(config: Config | None = None):
    if config.auto_update_enabled is False:
        return

    if config.auto_update_config_enabled is False:
        return

    config_url = config.auto_update_config_url
    if config_url is None:
        logger.output('No config URL provided, skipping config update.')

        return

    logger.output('Downloading latest config file from', config_url)

    try:
        last_modified_at = os.stat('config.json')[8]

        headers = {}
        if config.auto_update_config_token is not None:
            headers['Authorization'] = f'Bearer {config.auto_update_config_token}'

        response = requests.get(
            config_url,
            timeout=10,
            stream=True,
            headers=headers,
        )

        response_json = response.json()
        if 'error' in response_json:
            logger.output('Error fetching config file:', response_json['error'])

        elif response.status_code != 200:
            logger.output('Failed to fetch config file, status code:', response.status_code)

        elif 'config' not in response_json:
            logger.output('No config found in response, skipping config update.')

        elif 'config_updated_at' in response_json and response_json['config_updated_at'] <= last_modified_at:
            logger.output('Config file is up to date, no update needed.')

        else:
            with open('config.json', 'wb') as configfile:
                configfile.write(json.dumps(response_json['config']).encode('utf-8'))
                configfile.close()

            logger.output('Config file updated successfully.')

        response.close()

        del response
        del response_json

        gc.collect()

    except Exception as e:
        logger.output('Failed to update config file:', e)

def get_version(directory):
    try:
        if 'VERSION.txt' in os.listdir(directory):
            with open(directory + '/VERSION.txt') as f:
                version = f.read()

                f.close()

                return version
    except:
        pass

    return '0.0'

def get_latest_version(github_repo='alexbarnsley/esp32-solar-sensor', api_token: str | None = None):
    logger.output('Getting latest version from GitHub...')

    latest_release = requests.get(
        f'https://api.github.com/repos/{github_repo}/tags',
        headers=_headers(api_token),
        timeout=10,
        stream=True,
    )

    gh_json = latest_release.json()

    try:
        version = gh_json[0]['name']
    except KeyError as e:
        raise ValueError(
            "Release not found: \n",
            "Please ensure release as marked as 'latest', rather than pre-release \n",
            f"github api message: \n {gh_json} \n "
        ) from e

    latest_release.close()

    del latest_release
    del gh_json

    gc.collect()

    return version

def _download_new_version(version, github_src_dir, new_version_dir='next', github_repo='alexbarnsley/esp32-solar-sensor', api_token: str | None = None):
    logger.output(f'Downloading version {version}...')

    _download_all_files(version, github_src_dir, '', github_repo, new_version_dir, api_token)

    logger.output(f'Version {version} downloaded to {modulepath(new_version_dir)}')

def _download_all_files(version, github_src_dir, sub_dir='', github_repo='alexbarnsley/esp32-solar-sensor', new_version_dir='next', api_token: str | None = None):
    gc.collect()
    file_list = requests.get(
        f'https://api.github.com/repos/{github_repo}/contents{github_src_dir}{sub_dir}?ref=refs/tags/{version}',
        headers=_headers(api_token),
        timeout=10,
        stream=True,
    )

    file_list_json = file_list.json()

    logger.output('Getting file list from GitHub...', f'https://api.github.com/repos/{github_repo}/contents{github_src_dir}{sub_dir}?ref=refs/tags/{version}',)
    logger.output('File list JSON:', file_list_json)

    for file in file_list_json:
        if file['path'].startswith('.') or (file['path'].startswith('thirdparty') and file['type'] == 'dir'):
            logger.output('Skipping', file['path'])

            gc.collect()

            continue

        logger.output('Processing', file)
        logger.output(file['path'])

        git_path = file['path']

        if file['type'] == 'file':
            logger.output(f'\tDownloading: {git_path} to {git_path}')

            _download_file(version, git_path, github_repo, api_token, new_version_dir)
        elif file['type'] == 'dir':
            logger.output('Creating dir', git_path)

            mkdir(f'{new_version_dir}/{git_path}')
            _download_all_files(version, github_src_dir, sub_dir + '/' + file['name'], github_repo, new_version_dir, api_token)

        gc.collect()

    file_list.close()

def _download_file(version, git_path, github_repo='alexbarnsley/esp32-solar-sensor', api_token: str | None = None, new_version_dir='next'):
    response = requests.get(
        f'https://raw.githubusercontent.com/{github_repo}/{version}/{git_path}',
        headers=_headers(api_token),
        timeout=10,
        stream=True,
    )

    with open(f'{new_version_dir}/{git_path}', "wb") as out:
        out.write(response.content)
        out.close()

def _install_new_version(new_version_dir):
    logger.output('Installing new version at...')

    _copy_directory(modulepath(new_version_dir), '/')
    _rmtree(modulepath(new_version_dir))

    logger.output('Update installed, please reboot now')

def _rmtree(directory):
    if not _exists_dir(directory):
        return

    for entry in os.ilistdir(directory):
        is_dir = entry[1] == 0x4000
        if is_dir:
            _rmtree(directory + '/' + entry[0])
        else:
            os.remove(directory + '/' + entry[0])

    os.rmdir(directory)

def _copy_directory(from_path, to_path):
    if not _exists_dir(to_path):
        _mk_dirs(to_path)

    for entry in os.ilistdir(from_path):
        is_dir = entry[1] == 0x4000
        if is_dir:
            _copy_directory(from_path + '/' + entry[0], to_path + '/' + entry[0])
        else:
            _copy_file(from_path + '/' + entry[0], to_path + '/' + entry[0])

def _copy_file(from_path, to_path):
    with open(from_path) as from_file:
        with open(to_path, 'w') as to_file:
            CHUNK_SIZE = 512 # bytes
            data = from_file.read(CHUNK_SIZE)
            while data:
                to_file.write(data)
                data = from_file.read(CHUNK_SIZE)

            to_file.close()

        from_file.close()

def _exists_dir(path) -> bool:
    try:
        os.listdir(path)

        return True
    except:
        return False

def _mk_dirs(path:str):
    paths = path.split('/')

    path_to_create = ''
    for x in paths:
        mkdir(path_to_create + x)
        path_to_create = path_to_create + x + '/'

# different micropython versions act differently when directory already exists
def mkdir(path:str):
    try:
        os.mkdir(path)
    except OSError as exc:
        if exc.args[0] == 17:
            pass

def modulepath(path) -> str:
    return '/' + path
