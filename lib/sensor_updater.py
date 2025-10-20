# Heavily based on https://github.com/rdehuyss/micropython-ota-updater/blob/master/app/ota_updater.py

class SensorUpdater:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def install_update_if_available(self, mac_address: str) -> bool:
        import utime

        config_has_updated = self._download_config_file(mac_address)
        if config_has_updated:
            self.logger.output('Config file has been updated, rebooting.')

            import machine

            machine.reset()

        last_update_check = self.config.last_update_check
        if utime.time() - last_update_check < 3600:
            self.logger.output('Update check performed recently, skipping...')

            return False

        github_src_dir = self.config.update_github_src_dir

        github_repo = self.config.update_github_repo.rstrip('/').replace('https://github.com/', '')
        github_src_dir = '/' if github_src_dir is None or len(github_src_dir) < 1 else github_src_dir.rstrip('/') + '/'

        version_check_response = self._check_for_new_version(github_repo)
        if version_check_response is not None:
            (current_version, latest_version) = version_check_response
            if latest_version > current_version:
                self.logger.output(f'New version found - {latest_version}...')

                self._rmtree(self._modulepath(self.config.update_new_version_dir))

                self._mkdir(self._modulepath(self.config.update_new_version_dir))

                self._download_new_version(latest_version, github_src_dir, github_repo)
                self._install_new_version(latest_version)

                import gc

                gc.collect()

                return True

            self.logger.output('No new version found.')
        else:
            self.logger.output('Could not determine if new version is available. Pausing checks to avoid repeated failed attempts.')

        self.config.update_cache('last_update_check', utime.time())

        import gc

        gc.collect()

        return False

    @property
    def debug(self):
        return self.config.debug

    @property
    def github_request_headers(self):
        headers = {
            'User-Agent': 'esp32-solar-sensor-updater',
        }

        if self.config.update_api_token is not None:
            headers['Authorization'] = f'Bearer {self.config.update_api_token}'

        return headers

    @property
    def sensor_request_headers(self):
        headers = {
            'User-Agent': 'esp32-solar-sensor-updater',
        }

        if self.config.api_token is not None:
            headers['Authorization'] = f'Bearer {self.config.api_token}'

        return headers

    def _check_for_new_version(self, github_repo='alexbarnsley/esp32-solar-sensor'):
        current_version = self.config.version
        latest_version = self.get_latest_version(github_repo)

        if latest_version is None:
            self.logger.output('Could not get latest version, skipping update check.')

            return None

        self.logger.output('Checking version... ')
        self.logger.output('\tCurrent version: ', current_version)
        self.logger.output('\tLatest version: ', latest_version)

        return (current_version, latest_version)

    def _check_for_new_config(self, mac_address: str) -> bool:
        if self.config.auto_update_enabled is False:
            return

        if self.config.auto_update_config_enabled is False:
            return

        import utime

        if utime.time() - self.config.last_update_config_check < 3600:
            return

        self.config.update_cache('last_updated_config_check', utime.time())

        config_check_url = self.config.auto_update_config_check_url
        if config_check_url is None:
            self.logger.output('No config URL provided, skipping config update.')

            return

        has_update = False
        try:
            self.logger.output('Current config last modified at:', self.config.last_updated)

            import urequests as requests

            response = requests.get(
                config_check_url,
                timeout=10,
                stream=True,
                headers=self.sensor_request_headers,
                json={
                    "address": mac_address,
                }
            )

            self.logger.output('Checking if config file needs updating from', config_check_url, 'with headers', self.sensor_request_headers)

            response_json = response.json()
            self.logger.output('Config file response:', response_json)

            if 'error' in response_json:
                self.logger.output('Error fetching config file:', response_json['error'])

            elif response.status_code != 200:
                self.logger.output('Failed to fetch config file, status code:', response.status_code)

            elif 'config_updated_at' not in response_json:
                self.logger.output('No config found in response, skipping config update.')

            elif 'config_updated_at' in response_json and response_json['config_updated_at'] <= self.config.last_updated:
                self.logger.output(f'Config file is up to date, no update needed | config_updated_at: {response_json["config_updated_at"]} | last_updated: {self.config.last_updated}')

            else:
                has_update = True

            response.close()

            del response
            del response_json

        except OSError as e:
            if str(e.args[0]) != '-116':
                self.logger.output('OSError checking if config file needs updating:', e)
                if self.config.debug:
                    import sys

                    sys.print_exception(e)

                import machine

                machine.reset()

        except Exception as e:
            self.logger.output('Failed checking if config file needs updating:', e)
            if self.config.debug:
                import sys

                sys.print_exception(e)

        import gc

        gc.collect()

        return has_update

    def _download_config_file(self, mac_address: str) -> bool:
        if not self._check_for_new_config(mac_address):
            return False

        config_url = self.config.auto_update_config_url
        if config_url is None:
            self.logger.output('No config URL provided, skipping config update.')

            return

        self.logger.output('Downloading latest config file from', config_url)

        has_updated = False
        try:
            self.logger.output('Current config last modified at:', self.config.last_updated)

            import urequests as requests

            response = requests.get(
                config_url,
                timeout=10,
                stream=True,
                headers=self.sensor_request_headers,
                json={
                    "address": mac_address,
                }
            )

            response_json = response.json()
            self.logger.output('Config file response:', response_json)

            if 'error' in response_json:
                self.logger.output('Error fetching config file:', response_json['error'])

            elif response.status_code != 200:
                self.logger.output('Failed to fetch config file, status code:', response.status_code)

            elif 'config' not in response_json:
                self.logger.output('No config found in response, skipping config update.')

            else:
                from lib.utils import copy_file, json_dumps_with_indent

                with open('config.updated.json', 'wb') as configfile:

                    configfile.write(json_dumps_with_indent(response_json['config']).encode('utf-8'))
                    configfile.close()

                del configfile

                import os, utime

                copy_file('config.updated.json', 'config.json')
                os.remove('config.updated.json')

                self.config.update_cache('config_last_updated_at', response_json.get('config_updated_at', utime.time()))

                self.logger.output('Config file updated successfully.')

                has_updated = True

            response.close()

            del response
            del response_json

        except OSError as e:
            if str(e.args[0]) != '-116':
                self.logger.output('OSError updating config file:', e)
                if self.config.debug:
                    import sys

                    sys.print_exception(e)

                import machine

                machine.reset()

        except Exception as e:
            self.logger.output('Failed to update config file:', e)
            if self.config.debug:
                import sys

                sys.print_exception(e)

        import gc

        gc.collect()

        return has_updated

    def get_latest_version(self, github_repo='alexbarnsley/esp32-solar-sensor'):
        import gc, machine, sys
        import urequests as requests

        self.logger.output('Getting latest version from GitHub...')

        try:
            latest_release = requests.get(
                f'https://api.github.com/repos/{github_repo}/tags',
                headers=self.github_request_headers,
                timeout=10,
                stream=True,
            )

            gh_json = latest_release.json()

            version = None
            try:
                version = gh_json[0]['name']

            except OSError as e:
                if str(e.args[0]) != '-116':
                    self.logger.output(f'OSError getting latest version: {e}')

                    machine.reset()

            except KeyError as e:
                self.logger.output(
                    "Release not found: \n",
                    "Please ensure release as marked as 'latest', rather than pre-release \n",
                    f"github api message: \n {gh_json} \n "
                )

                if self.config.debug:
                    sys.print_exception(e)

            latest_release.close()

            del latest_release
            del gh_json

        except OSError as e:
            if str(e.args[0]) != '-116':
                self.logger.output('OSError getting latest version:', e)
                if self.config.debug:
                    sys.print_exception(e)

                machine.reset()

        except Exception as e:
            self.logger.output('Failed getting latest version:', e)
            if self.config.debug:
                sys.print_exception(e)

        gc.collect()

        return version

    def _download_all_files(self, version, github_src_dir, sub_dir='', github_repo='alexbarnsley/esp32-solar-sensor'):
        import gc, machine, sys, utime
        import urequests as requests

        gc.collect()

        try:
            file_list = requests.get(
                f'https://api.github.com/repos/{github_repo}/contents{github_src_dir}{sub_dir}?ref=refs/tags/{version}',
                headers=self.github_request_headers,
                timeout=10,
                stream=True,
            )

            file_list_json = file_list.json()

            self.logger.output('Getting file list from GitHub...', f'https://api.github.com/repos/{github_repo}/contents{github_src_dir}{sub_dir}?ref=refs/tags/{version}',)
            self.logger.output('File list JSON:', file_list_json)

            for file in file_list_json:
                if file['path'].startswith('.') or (file['path'].startswith('thirdparty') and file['type'] == 'dir'):
                    self.logger.output('Skipping', file['path'])

                    gc.collect()

                    continue

                self.logger.output('Processing', file)
                self.logger.output(file['path'])

                git_path = file['path']

                if file['type'] == 'file':
                    self.logger.output(f'\tDownloading: {git_path} to {git_path}')

                    self._download_file(version, git_path, github_repo)
                elif file['type'] == 'dir':
                    self.logger.output('Creating dir', git_path)

                    self._mkdir(f'{self.config.update_new_version_dir}/{git_path}')
                    self._download_all_files(version, github_src_dir, sub_dir + '/' + file['name'], github_repo)

                utime.sleep(0.1)

                gc.collect()

            file_list.close()

            del file_list
            del file_list_json

        except OSError as e:
            self.logger.output('OSError downloading files:', e)
            if self.config.debug:
                sys.print_exception(e)

            machine.reset()

        except Exception as e:
            self.logger.output('Failed to downloading files:', e)
            if self.config.debug:
                sys.print_exception(e)

        gc.collect()

    def _download_file(self, version, git_path, github_repo='alexbarnsley/esp32-solar-sensor'):
        import machine, sys
        import urequests as requests

        try:
            response = requests.get(
                f'https://raw.githubusercontent.com/{github_repo}/{version}/{git_path}',
                headers=self.github_request_headers,
                timeout=10,
                stream=True,
            )

            with open(f'{self.config.update_new_version_dir}/{git_path}', "wb") as out:
                out.write(response.content)
                out.close()

        except OSError as e:
            self.logger.output(f'OSError download file "{git_path}":', e)
            if self.config.debug:
                sys.print_exception(e)

            machine.reset()

        except Exception as e:
            self.logger.output(f'Failed download file "{git_path}":', e)
            if self.config.debug:
                sys.print_exception(e)

    def _download_new_version(self, version, github_src_dir, github_repo='alexbarnsley/esp32-solar-sensor'):
        self.logger.output(f'Downloading version {version}...')

        self._download_all_files(version, github_src_dir, '', github_repo)

        self.logger.output(f'Version {version} downloaded to {self._modulepath(self.config.update_new_version_dir)}')

    def _install_new_version(self, latest_version):
        self.logger.output('Installing new version at...')

        self._copy_directory(self._modulepath(self.config.update_new_version_dir), '/')
        self._rmtree(self._modulepath(self.config.update_new_version_dir))

        self.logger.output('Update installed')

        self.config.update_cache('version', latest_version)

    def _rmtree(self, directory):
        import os

        if not self._exists_dir(directory):
            return

        for entry in os.ilistdir(directory):
            is_dir = entry[1] == 0x4000
            if is_dir:
                self._rmtree(directory + '/' + entry[0])
            else:
                os.remove(directory + '/' + entry[0])

        os.rmdir(directory)

    def _copy_directory(self, from_path, to_path):
        import os
        from lib.utils import copy_file

        if not self._exists_dir(to_path):
            self._mk_dirs(to_path)

        for entry in os.ilistdir(from_path):
            is_dir = entry[1] == 0x4000
            if is_dir:
                self._copy_directory(from_path + '/' + entry[0], to_path + '/' + entry[0])
            else:
                copy_file(from_path + '/' + entry[0], to_path + '/' + entry[0])

    def _exists_dir(self, path) -> bool:
        import os, machine

        try:
            os.listdir(path)

            return True

        except OSError as e:
            if e.args[0] != 2:
                print(f'OSError checking directory exists: {e}')

                machine.reset()

        except:
            return False

    def _mk_dirs(self, path: str):
        paths = path.split('/')

        path_to_create = ''
        for x in paths:
            self._mkdir(path_to_create + x)
            path_to_create = path_to_create + x + '/'

    # different micropython versions act differently when directory already exists
    def _mkdir(self, path: str):
        import os

        try:
            os.mkdir(path)
        except OSError as exc:
            if exc.args[0] == 17:
                pass

    def _modulepath(self, path) -> str:
        return '/' + path
