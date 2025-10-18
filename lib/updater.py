# Based on https://github.com/rdehuyss/micropython-ota-updater/blob/master/app/ota_updater.py

import os
import gc
import utime

import requests

last_check_timestamp = 0

def install_update_if_available(
    github_repo,
    github_src_dir='',
    module='',
    main_dir='main',
    new_version_dir='next',
    config_file=None,
    check_frequency_seconds=3600,
    api_token: str | None = None,
) -> bool:
    """This method will immediately install the latest version if out-of-date.

    This method expects an active internet connection and allows you to decide yourself
    if you want to install the latest version. It is necessary to run it directly after boot
    (for memory reasons) and you need to restart the microcontroller if a new version is found.

    Returns
    -------
        bool: true if a new version is available, false otherwise
    """

    global last_check_timestamp

    if utime.time() - last_check_timestamp < check_frequency_seconds:
        return False

    github_repo = github_repo.rstrip('/').replace('https://github.com/', '')
    github_src_dir = '/' if len(github_src_dir) < 1 else github_src_dir.rstrip('/') + '/'
    module = module.rstrip('/')

    (current_version, latest_version) = _check_for_new_version(main_dir, github_repo, module)
    if latest_version > current_version:
        print(f'Updating to version {latest_version}...')
        _create_new_version_file(latest_version, new_version_dir, module)
        _download_new_version(latest_version, new_version_dir, main_dir, github_repo, github_src_dir, module, api_token)
        _copy_config_file(main_dir, new_version_dir, config_file, module)
        _delete_old_version(main_dir, module)
        _install_new_version(main_dir, module)

        last_check_timestamp = utime.time()

        return True

    last_check_timestamp = utime.time()

    return False

def _headers(api_token: str | None = None) -> dict[str, str]:
    headers = {
        'User-Agent': 'esp32-solar-sensor-updater',
    }

    if api_token is not None:
        headers['Authorization'] = f'Bearer {api_token}'

    return headers

def _check_for_new_version(main_dir: str, github_repo='alexbarnsley/esp32-solar-sensor', module='', api_token: str | None = None):
    current_version = get_version(modulepath(main_dir, module))
    latest_version = get_latest_version(github_repo, api_token)

    print('Checking version... ')
    print('\tCurrent version: ', current_version)
    print('\tLatest version: ', latest_version)

    return (current_version, latest_version)

def _create_new_version_file(latest_version, new_version_dir='next', module=''):
    mkdir(modulepath(new_version_dir, module))
    with open(modulepath(new_version_dir + '/.version', module), 'w') as versionfile:
        versionfile.write(latest_version)
        versionfile.close()

def get_version(directory, version_file_name='.version'):
    try:
        if version_file_name in os.listdir(directory):
            with open(directory + '/' + version_file_name) as f:
                version = f.read()

                return version
    except:
        pass

    return '0.0'

def get_latest_version(github_repo='alexbarnsley/esp32-solar-sensor', api_token: str | None = None):
    print('Getting latest version from GitHub...', f'https://api.github.com/repos/{github_repo}/releases/latest')

    latest_release = requests.get(
        f'https://api.github.com/repos/{github_repo}/releases/latest',
        headers=_headers(api_token),
        timeout=10,
    )

    print('ASDASdASDs', latest_release.content.decode('utf-8'))

    gh_json = latest_release.json()

    try:
        version = gh_json['tag_name']
    except KeyError as e:
        raise ValueError(
            "Release not found: \n",
            "Please ensure release as marked as 'latest', rather than pre-release \n",
            f"github api message: \n {gh_json} \n "
        ) from e

    latest_release.close()

    return version

def _download_new_version(version, new_version_dir='next', main_dir='main', github_repo='alexbarnsley/esp32-solar-sensor', github_src_dir='', module='', api_token: str | None = None):
    print(f'Downloading version {version}')

    _download_all_files(version, '', github_repo, new_version_dir, main_dir, github_src_dir, module, api_token)

    print(f'Version {version} downloaded to {modulepath(new_version_dir, module)}')

def _download_all_files(version, sub_dir='', github_repo='alexbarnsley/esp32-solar-sensor', new_version_dir='next', main_dir='main', github_src_dir='', module='', api_token: str | None = None):
    gc.collect()
    file_list = requests.get(
        f'https://api.github.com/repos/{github_repo}/contents{github_src_dir}{sub_dir}?ref=refs/tags/{version}',
        headers=_headers(api_token),
        timeout=10,
    )

    file_list_json = file_list.json()

    print('Getting file list from GitHub...', f'https://api.github.com/repos/{github_repo}/contents{github_src_dir}{sub_dir}?ref=refs/tags/{version}',)
    print('File list JSON:', file_list_json)

    for file in file_list_json:
        print('Processing', file)
        print(file['path'])

        path = modulepath(new_version_dir + '/' + file['path'].replace(main_dir + '/', '').replace(github_src_dir, ''), module)
        if file['type'] == 'file':
            git_path = file['path']
            print(f'\tDownloading: {git_path} to {path}')
            _download_file(version, git_path, path, github_repo, api_token)
        elif file['type'] == 'dir':
            print('Creating dir', path)
            mkdir(path)
            _download_all_files(version, sub_dir + '/' + file['name'], github_repo, new_version_dir, main_dir, github_src_dir, module, api_token)
        gc.collect()

    file_list.close()

def _download_file(version, git_path, path, github_repo='alexbarnsley/esp32-solar-sensor', api_token: str | None = None):
    requests.get(
        f'https://raw.githubusercontent.com/{github_repo}/{version}/{git_path}',
        headers=_headers(api_token),
        saveToFile=path,
        timeout=10,
    )

def _copy_config_file(main_dir='main', new_version_dir='next', config_file=None, module=''):
    if config_file:
        from_path = modulepath(main_dir + '/' + config_file, module)
        to_path = modulepath(new_version_dir + '/' + config_file, module)

        print(f'Copying secrets file from {from_path} to {to_path}')

        _copy_file(from_path, to_path)

        print(f'Copied secrets file from {from_path} to {to_path}')

def _delete_old_version(main_dir='main', module=''):
    print(f'Deleting old version at {modulepath(main_dir, module)} ...')

    _rmtree(modulepath(main_dir, module))

    print(f'Deleted old version at {modulepath(main_dir, module)} ...')

def _install_new_version(main_dir='main', module=''):
    print(f'Installing new version at {modulepath(main_dir, module)} ...')

    # if _os_supports_rename():
    #     os.rename(modulepath(new_version_dir), modulepath(main_dir))
    # else:
    #     _copy_directory(modulepath(new_version_dir), modulepath(main_dir))
    #     _rmtree(modulepath(new_version_dir))

    print('Update installed, please reboot now')

def _rmtree(directory):
    for entry in os.ilistdir(directory):
        is_dir = entry[1] == 0x4000
        if is_dir:
            _rmtree(directory + '/' + entry[0])
        else:
            os.remove(directory + '/' + entry[0])

    os.rmdir(directory)

def _os_supports_rename() -> bool:
    _mk_dirs('otaUpdater/osRenameTest')
    os.rename('otaUpdater', 'otaUpdated')
    result = len(os.listdir('otaUpdated')) > 0
    _rmtree('otaUpdated')

    return result

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
    with open(from_path) as fromFile:
        with open(to_path, 'w') as toFile:
            CHUNK_SIZE = 512 # bytes
            data = fromFile.read(CHUNK_SIZE)
            while data:
                toFile.write(data)
                data = fromFile.read(CHUNK_SIZE)

        toFile.close()

    fromFile.close()

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

def modulepath(path, module='') -> str:
    return module + '/' + path if module else path
