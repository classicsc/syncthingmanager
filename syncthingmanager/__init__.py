""" A module providing high-level methods for the Syncthing API, and a script
    using them. """
#    Copyright (C) 2017  Samuel Smoker
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from syncthing import Syncthing, SyncthingError
from argparse import ArgumentParser
import configparser
import pathlib
import sys
import os
from xml.etree.ElementTree import parse
from textwrap import dedent
import platform
import requests

# Put globals here
__VERSION__ = '0.1.0'
__DEFAULT_CONFIG_LOCATION__ = '$HOME/.config/syncthingmanager/syncthingmanager.conf'
if platform.system() == 'Windows':
    __DEFAULT_ST_CONFIG_LOCATION__ = '%localappdata%/Syncthing/config.xml'
elif platform.system() == 'Darwin':
    __DEFAULT_ST_CONFIG_LOCATION__ = '$HOME/Library/Application Support/Syncthing/config.xml'
else:
    __DEFAULT_ST_CONFIG_LOCATION__ = '$HOME/.config/syncthing/config.xml'

# Some terminal colors
HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'


class SyncthingManagerError(Exception):
    pass


class SyncthingManager(Syncthing):
    def device_info(self, devicestr):
        """ A helper for finding a device ID from a user string that may be a
        deviceID a device name.

        Args:
            devicestr (str): the string that may be a deviceID or configured
                device name.

        Returns:
            dict:

                id: The deviceID in modern format, or None if not recogized.

                index: the index of the device in config['devices'] in the
                    current configuration, or None if not configured.

                folders: a list of folder IDs associated with the device."""

        try:
            device_id = self.misc.device_id(devicestr)
        except SyncthingError:
            device_id = None
        deviceindex = None
        device_name = None
        config = self.system.config()
        folders = []
        if not device_id:
            for index, device in enumerate(config['devices']):
                if devicestr == device['name']:
                    device_name = device['name']
                    device_id = device['deviceID']
                    deviceindex = index
                    for folder in config['folders']:
                        for d in folder['devices']:
                            if d['deviceID'] == device_id:
                                folders.append(folder['id'])
                    break
        else:
            for index, device in enumerate(config['devices']):
                if device_id == device['deviceID']:
                    deviceindex = index
                    device_name = device['name']
                    for folder in config['folders']:
                        for d in folder['devices']:
                            if device['deviceID'] == d['deviceID']:
                                folders.append(folder['id'])
                    break
        return {'id': device_id, 'index': deviceindex, 'folders': folders,
                'name': device_name}

    def folder_info(self, folderstr):
        """Looks for a configured folder based on a user-input string and
        returns some useful info about it. Looks for a matching ID first,
        only considers labels if none is found. Further, duplicate labels
        are not reported. The first matching label in the config is used.

        Args:

            folderstr (str): the folder ID or label

        returns:

            dict:

                id: (str) the folder ID

                index: (str) the index of the folder in the active configuration

                label: (str) the folder label

                devices: (list) the deviceIDs associated with the folder

            None if no matching folder found """
        config = self.system.config()
        for index, folder in enumerate(config['folders']):
            if folder['id'] == folderstr:
                info = dict()
                info['id'] = folder['id']
                info['index'] = index
                info['label'] = folder['label']
                info['devices'] = folder['devices']
                return info
        for index, folder in enumerate(config['folders']):
            if folder['label'] == folderstr:
                info = dict()
                info['id'] = folder['id']
                info['index'] = index
                info['label'] = folder['label']
                info['devices'] = folder['devices']
                return info
        return None

    def daemon_pause(self, device):
        """ Pause one or all devices.

            Args:

                device (str): the device to be paused

            Returns:
                None """
        device_id = self.device_info(device)['id']
        r = self.system.pause(device_id)
        if r['error']:
            raise SyncthingManagerError(r['error'])

    def daemon_resume(self, device):
        """ Resume one or all devices.

            Args:
                device (str): the device to be resumed

            Returns:
                None """
        device_id = self.device_info(device)['id']
        r = self.system.resume(device_id)
        if r['error']:
            raise SyncthingManagerError(r['error'])

    def add_device(self, device_id, name='', address='', dynamic=False,
            introducer=False):
        """ Adds a device to the configuration and sets the configuration.

        Args:

            device_id (str): The device ID to be added.

            address (str): An address to initialize the address list.

            name (str): The name of the device. default: ``''``

            dynamic (bool): Add the ``dynamic`` entry to the addresses. No
                effect if ``addresses`` is not specified. default: ``False``

            introducer (bool): Give the device the introducer flag.
                default: ``False``

        Returns:

            None """
        config = self.system.config()
        info = self.device_info(device_id)
        if not info['id']:
            raise SyncthingManagerError("Bad device ID: " + device_id)
        if isinstance(info['index'], int):
            raise SyncthingManagerError("Device already configured: " + device_id)
        else:
            addresses = [address]
            if dynamic:
                addresses.append('dynamic')
            config['devices'].append({'deviceID': info['id'], 'name': name,
                'addresses': addresses, 'compression': 'metadata',
                'certName': '', 'introducer': introducer})
            self.system.set_config(config)

    def remove_device(self, devicestr):
        """Removes a device from the configuration and sets it.

        Args:

            devicestr (str): The device ID or name.

        Returns:

            None

        Raises: ``SyncthingManagerError``: when the given device is not
            configured. """
        config = self.system.config()
        info = self.device_info(devicestr)
        if info['index'] == None:
            raise SyncthingManagerError("Device not configured: " + devicestr)
        else:
            del config['devices'][info['index']]
            self.system.set_config(config)

    def edit_device(self, devicestr, prop, value):
        """Changes properties of a device's configuration.

        Args:

            devicestr (str): The device ID or name.

            prop (str): the property as in the REST config documentaion

            value: the new value of the property. Needs to be in a
                serializable format accepted by the API.

        Returns:

            None

        Raises: ``SyncthingManagerError``: when the given device is not configured."""
        config = self.system.config()
        info = self.device_info(devicestr)
        if info['index'] is None:
            raise SyncthingManagerError("Device not configured: " + devicestr)
        else:
            config['devices'][info['index']][prop] = value
            self.system.set_config(config)

    def device_change_name(self, devicestr, name):
        """Set or change the name of a configured device.

        Args:

            devicestr (str): the device ID or current name.

            name (str): the new device name."""
        self.edit_device(devicestr, 'name', name)

    def device_add_address(self, devicestr, address):
        """Add an address to the device's list of addresses.

        Args:

            devicestr(str): the device ID or name.

            address(str): a tcp://address to add.
        """
        info = self.device_info(devicestr)
        try:
            addresses = self.system.config()['devices'][info['index']]['addresses']
        except TypeError:
            raise SyncthingManagerError('Device not configured: ' + devicestr)
        addresses.append(address)
        self.edit_device(devicestr, 'addresses', addresses)

    def device_remove_address(self, devicestr, address):
        """The inverse of device_add_address."""
        info = self.device_info(devicestr)
        try:
            addresses = self.system.config()['devices'][info['index']]['addresses']
        except TypeError:
            raise SyncthingManagerError('Device not configured: ' + devicestr)
        try:
            addresses.remove(address)
            self.edit_device(devicestr, 'addresses', addresses)
        except ValueError:
            pass

    def add_folder(self, path, folderid, label='', foldertype='readwrite',
            rescan=60):
        """Adds a folder to the configuration and sets it.

        Args:

            path (str): a path to the folder to be configured, either absolute
                or relative to the cwd.

            folderid (str): the string to identify the folder (must be same
                on every device)

            label (str): the label used as an alternate, local name for the
                folder.

            foldertype (str): see syncthing documentation...

            rescan (int): the interval for scanning in seconds.

        Returns:

            None

        Raises:

            ``SyncthingManagerError``: when the path is invalid

            ``SyncthingManagerError``: when a folder with identical label is
                already configured. """
        config = self.system.config()
        # It's allowed to have a folder ID that matches another folder's label
        # so we have to be careful about finding an in-use folder ID.
        identicalid = lambda x: x['id'] == folderid
        if next(filter(identicalid, config['folders']), None):
            raise SyncthingManagerError("The folder ID " + folderid +
                    " is already in use")
        else:
            try:
                path = pathlib.Path(path).resolve()
            except FileNotFoundError:
                raise SyncthingManagerError("There was a problem with the path "
                        "entered: " + path)
            folder = {'id': folderid, 'label': label, 'path': str(path),
                'type': foldertype, 'rescanIntervalS': int(rescan), 'fsync': True,
                'autoNormalize': True, 'maxConflicts': 10, 'pullerSleepS': 0,
                'minDiskFreePct': 1}
            config['folders'].append(folder)
            self.system.set_config(config)

    def remove_folder(self, folderstr):
        """Removes a folder from the configuration and sets it.

        Args:

            folderstr (str): an item from user input that may be the folder ID
                or label.

        Returns:

            None"""
        info = self.folder_info(folderstr)
        if not info:
            raise SyncthingManagerError(folderstr + " is not the ID or label "
                    "of a configured folder.")
        config = self.system.config()
        del config['folders'][info['index']]
        self.system.set_config(config)

    def share_folder(self, folderstr, devicestr):
        """ Adds a device to a folder's list of devices and sets the
        configuration.

        Args:

            folderstr (str): an item from user input that may be the folder ID
                or label.

            devicestr (str): an item from user input that may be the device ID
                or name.

        Returns:

            None """
        info = self.folder_info(folderstr)
        if not info:
            raise SyncthingManagerError(folderstr + " is not the ID or label "
                    "of a configured folder.")
        deviceinfo = self.device_info(devicestr)
        if deviceinfo['index'] is None:
            raise SyncthingManagerError(devicestr + " is not a configured"
                     " device name or ID")
        for device in info['devices']:
            if device['deviceID'] == deviceinfo['id']:
                raise SyncthingManagerError(devicestr + " is already "
                        "associated with " + folderstr)
        config = self.system.config()
        info['devices'].append(dict({'deviceID': deviceinfo['id']}))
        config['folders'][info['index']]['devices'] = info['devices']
        self.system.set_config(config)

    def unshare_folder(self, folderstr, devicestr):
        """ Removes a device from a folder's list of devices and sets the
                configuration.

        Args:

            folderstr (str): an item from user input that may be the folder ID
                or label.

            devicestr (str): an item from user input that may be the device ID
                or name.

        Returns:

            None """
        info = self.folder_info(folderstr)
        if not info:
            raise SyncthingManagerError(folderstr + " is not the ID or label "
                    "of a configured folder.")
        deviceinfo = self.device_info(devicestr)
        if deviceinfo['index'] is None:
            raise SyncthingManagerError(devicestr + " is not a configured "
                    "device name or ID")
        config = self.system.config()
        for index, device in enumerate(info['devices']):
            if device['deviceID'] == deviceinfo['id']:
                del info['devices'][index]
                config['folders'][info['index']]['devices'] = info['devices']
                self.system.set_config(config)
                return
        raise SyncthingManagerError(devicestr + " is not associated with "
                + folderstr)

    def folder_edit(self, folderstr, prop, value):
        config = self.system.config()
        info = self.folder_info(folderstr)
        if info['index'] is None:
            raise SyncthingManagerError("Folder not configured: " + folderstr)
        else:
            config['folders'][info['index']][prop] = value
            self.system.set_config(config)

    def folder_set_label(self, folderstr, label):
        self.folder_edit(folderstr, 'label', label)

    def folder_set_rescan(self, folderstr, rescan):
        self.folder_edit(folderstr, 'rescanIntervalS', int(rescan))

    def folder_set_minfree(self, folderstr, minfree):
        self.folder_edit(folderstr, 'minDiskFreePct', int(minfree))

    def folder_set_type(self, folderstr, folder_type):
        self.folder_edit(folderstr, 'type', folder_type)

    def folder_set_order(self, folderstr, order):
        self.folder_edit(folderstr, 'order', order)

    def folder_set_ignore_perms(self, folderstr, ignore):
        self.folder_edit(folderstr, 'ignorePerms', ignore)

    def folder_setup_versioning_trashcan(self, folderstr, cleanoutdays):
        versioning = {'params': {'cleanoutDays': str(cleanoutdays)}, 'type':
            'trashcan'}
        self.folder_edit(folderstr, 'versioning', versioning)

    def folder_setup_versioning_simple(self, folderstr, keep):
        versioning = {'params': {'keep': str(keep)}, 'type': 'simple'}
        self.folder_edit(folderstr, 'versioning', versioning)

    def folder_setup_versioning_staggered(self, folderstr, maxage, path):
        maxage = maxage*24*60**2  # Convert to seconds
        versioning = {'params': {'maxAge': str(maxage), 'cleanInterval': '3600',
            'versionsPath': path}, 'type': 'staggered'}
        self.folder_edit(folderstr, 'versioning', versioning)

    def folder_setup_versioning_external(self, folderstr, command):
        versioning = {'params': {'command': command}, 'type': 'external'}
        self.folder_edit(folderstr, 'versioning', versioning)

    def folder_setup_versioning_none(self, folderstr):
        versioning = {'params': {}, 'type': ''}
        self.folder_edit(folderstr, 'versioning', versioning)

    def _print_device_info(self, devicestr):
        config = self.system.config()
        info = self.device_info(devicestr)
        try:
            device = config['devices'][info['index']]
        except TypeError:
            raise SyncthingManagerError("Device not configured: " + devicestr)
        folders = self.device_info(device['deviceID'])['folders']
        outstr = """\
                {0}
                    Addresses:     {1}
                    Folders:    {2}
                    ID:     {3}
                    Introducer?     {4}
                """.format(device['name'], ', '.join(device['addresses']),
                ', '.join(map(str, folders)), device['deviceID'],
                device['introducer'])
        print(dedent(outstr))

    def _device_list(self):
        """Prints out a formatted list of devices and their state from the
            active configuration."""
        config = self.system.config()
        connections = self.system.connections()['connections']
        status = self.system.status()
        connected = []
        not_connected = []
        for device in config['devices']:
            if device['deviceID'] == status['myID']:
                this_device = device
                continue
            elif connections[device['deviceID']]['connected']:
                connected.append(device)
                continue
            else:
                not_connected.append(device)
        outstr = """\
                {0}     This Device
                    ID:     {1}
                """.format(this_device['name'], this_device['deviceID'])
        print(dedent(outstr))
        for device in connected:
            address = connections[device['deviceID']]['address']
            folders = self.device_info(device['deviceID'])['folders']
            outstr = """\
                    {0}     {1}Connected{2}
                        At:     {3}
                        Folders:    {4}
                        ID:     {5}
                    """.format(device['name'], OKGREEN, ENDC, address,
                    ', '.join(map(str, folders)), device['deviceID'])
            print(dedent(outstr))

        for device in not_connected:
            folders = self.device_info(device['deviceID'])['folders']
            outstr = """\
                    {0}     {1}Not Connected{2}
                        Folders:    {3}
                        ID:     {4}
                    """.format(device['name'], FAIL, ENDC,
                    ', '.join(map(str, folders)), device['deviceID'])
            print(dedent(outstr))

    def _print_folder_info(self, folderstr):
        info = self.folder_info(folderstr)
        config = self.system.config()
        try:
            folder = config['folders'][info['index']]
        except TypeError:
            raise SyncthingManagerError("Folder not configured: " + folderstr)
        status = self.system.status()
        devices = []
        for device in folder['devices']:
            if device['deviceID'] == status['myID']:
                continue
            name = self.device_info(device['deviceID'])['name']
            devices.append(name)
        if folder['label'] == '':
            folderstr = folder['id']
        else:
            folderstr = folder['label']
        nondefaults = ""
        if folder['rescanIntervalS'] != 60:
            nondefaults += ('    Rescan Interval:    ' +
                    str(folder['rescanIntervalS']))
        if folder['type'] != 'readwrite':
            nondefaults += ('\n    Folder Type:      ' +
                    folder['type'])
        if folder['order'] != 'random':
            nondefaults += ('\n    File Pull Order:  ' +
                    folder['order'])
        if folder['versioning']['type'] != '':
            nondefaults += ('\n    Versioning:       ' +
                    folder['versioning']['type'])
            if folder['versioning']['type'] == 'trashcan':
                nondefaults += ('\n    Clean out after:    ' +
                        folder['versioning']['params']['cleanoutDays'])
            if folder['versioning']['type'] == 'simple':
                nondefaults += ('\n    Keep Versions:      ' +
                        folder['versioning']['params']['keep'])
            if folder['versioning']['type'] == 'staggered':
                nondefaults += ('\n    Versions Path:      ' +
                        folder['versioning']['params']['versionsPath'])
            if folder['versioning']['type'] == 'external':
                nondefaults += ('\n    Command:            ' +
                        folder['versioning']['params']['command'])
        outstr = """\
                {0}
                    Shared With:  {1}
                    Folder ID:  {2}
                    Folder Path:    {3}\
                """.format(folderstr, ', '.join(map(str, devices)),
                        folder['id'], folder['path'])
        print(dedent(outstr))
        print(nondefaults)


    def _folder_list(self):
        """Prints out a formatted list of folders from the configuration."""
        config = self.system.config()
        status = self.system.status()
        for folder in config['folders']:
            devices = []
            for device in folder['devices']:
                if device['deviceID'] == status['myID']:
                    continue
                name = self.device_info(device['deviceID'])['name']
                devices.append(name)
            if folder['label'] == '':
                folderstr = folder['id']
            else:
                folderstr = folder['label']
            outstr = """\
                    {0}
                        Shared With:  {1}
                        Folder ID:  {2}
                        Folder Path:    {3}
                    """.format(folderstr, ', '.join(map(str, devices)),
                            folder['id'], folder['path'])
            print(dedent(outstr))


def arguments():
    parser = ArgumentParser()
    parser.add_argument('--config', '-c', default=__DEFAULT_CONFIG_LOCATION__,
            help="stman configuration file")
    parser.add_argument('--device', '-d', metavar='NAME', default='DEFAULT',
            help="the configured API to use", dest='config_device')
    base_subparsers = parser.add_subparsers(dest='subparser_name',
            metavar='action')
    base_subparsers.required = True

    configuration_parser = base_subparsers.add_parser('configure',
            help="configure stman. If the configuration file specified in "
            "-c (or the default) does not exist, it will be created. To edit an " +
            "existing configuration, specify all options again.")
    configuration_parser.add_argument('-k', '--apikey', help="the Syncthing API key, "
            + "found in the GUI or config.xml", default=None)
    configuration_parser.add_argument('--hostname', '-a', default='localhost',
            help="the hostname to use. default localhost.")
    configuration_parser.add_argument('--port', '-p', default='8384',
            help="the port to use. Default 8384", type=int)
    configuration_parser.add_argument('--name', '-n',
            help="what to call this device. Defaults to the hostname.")
    configuration_parser.add_argument('--default', action='store_true',
            help="make this device the default.")

    daemon_parser = base_subparsers.add_parser('daemon', help="control synchronization activity by device or folder.")
    daemon_parser.add_argument('-p', '--pause', help="pause syncing with a device")
    daemon_parser.add_argument('-r', '--resume', help='resume syncing with a device')
    # This stuff should be in 0.14.25, uncomment when it goes stable.
#    daemon_parser.add_argument('--pause-all', action='store_true', help="pause syncing with all devices")
#    daemon_parser.add_argument('--resume-all', action='store_true', help="resume syncing with all devices")

    device_parser = base_subparsers.add_parser('device',
            help="work with devices")
    device_subparsers = device_parser.add_subparsers(dest='deviceparser_name',
            metavar='ACTION')
    device_subparsers.required = True
    add_device_parser = device_subparsers.add_parser('add',
            help="configure a device")
    add_device_parser.set_defaults(name='', address='')
    add_device_parser.add_argument('deviceID', metavar='DEVICEID', help="the deviceID to be configured.")
    add_device_parser.add_argument('-n', '--name', help="a short name for the device.")
    add_device_parser.add_argument('-d', '--dynamic', action='store_true',
            help="adds 'dynamic' to the list of hosts. Unnecessary if no hostname specified.")
    add_device_parser.add_argument('-a', '--address',
            help="hostname, including leading 'tcp://'. Default dynamic.")
    add_device_parser.add_argument('-i', '--introducer', action='store_true',
            help="makes this device an introducer.")

    device_info_parser = device_subparsers.add_parser('info',
            help="shows detailed device information")
    device_info_parser.add_argument('device', metavar='DEVICE',
            help="the device name or ID")

    list_device_parser = device_subparsers.add_parser('list',
            help="shows a list of devices and some information")

    remove_device_parser = device_subparsers.add_parser('remove',
            help="remove a device")
    remove_device_parser.add_argument('device', metavar='DEVICE', help="the name or ID to be removed")

    edit_device_parser = device_subparsers.add_parser('edit',
            help="edit device properties")
    edit_device_parser.add_argument('device', metavar='DEVICE', help='the device name or ID to edit')
    edit_device_parser.add_argument('-n', '--name', metavar='NAME', help='set or change the device name')
    edit_device_parser.add_argument('-a', '--add-address', metavar='ADDRESS',
            help='add ADDRESS to the list of hosts')
    edit_device_parser.add_argument('-r', '--remove-address', metavar='ADDRESS',
            help='remove ADDRESS from the list of hosts')
    edit_device_parser.add_argument('-c', '--compression', metavar='SETTING',
            help='the level of compression to use', choices=['always', 'metadata', 'never'])
    edit_device_parser.add_argument('-i', '--introducer', action='store_true',
            help='set the device as an introducer')
    edit_device_parser.add_argument('-io', '--introducer-off', action='store_true',
            help='toggle the introducer setting off')

    folder_parser = base_subparsers.add_parser('folder',
            help="work with folders")
    folder_subparsers = folder_parser.add_subparsers(dest='folderparser_name',
            metavar='action')
    folder_subparsers.required = True
    add_folder_parser = folder_subparsers.add_parser('add',
            help="Configure a folder")
    add_folder_parser.add_argument('path', metavar='PATH', help="path to the folder to be added")
    add_folder_parser.add_argument('folderID', metavar='ID',
            help="the folder ID. Must match the one used on all cluster devices.")
    add_folder_parser.add_argument('--label', '-l', help="a local name for the folder")
    add_folder_parser.add_argument('--foldertype', '-t', default='readwrite',
            help="'readwrite' or 'readonly'. Default readwrite", choices=['readwrite', 'readonly'])
    add_folder_parser.add_argument('--rescan-interval', '-r', default=60, type=int,
            help='time in seconds between scanning for changes. Default 60.')

    remove_folder_parser = folder_subparsers.add_parser('remove',
            help='Remove a folder')
    remove_folder_parser.add_argument('folder', metavar='FOLDER',
            help='either the folder ID or label')

    share_folder_parser = folder_subparsers.add_parser('share',
            help='Share a folder')
    share_folder_parser.add_argument('folder', metavar='FOLDER', help='the folder ID or label')
    share_folder_parser.add_argument('device', metavar='DEVICE', help='the device ID or label')

    unshare_folder_parser = folder_subparsers.add_parser('unshare',
            help='Stop sharing folder with device')
    unshare_folder_parser.add_argument('folder', metavar='FOLDER', help='the folder ID or label')
    unshare_folder_parser.add_argument('device', metavar='DEVICE', help='the device ID or name')

    edit_folder_parser = folder_subparsers.add_parser('edit',
            help="modify a configured folder")
    edit_folder_parser.add_argument('folder', metavar='FOLDER', help='the folder ID or label')
    edit_folder_parser.add_argument('--label', '-n', metavar='LABEL',
            help='the label to be set')
    edit_folder_parser.add_argument('--rescan', '-r', metavar='INTERVAL',
            help="the time (in seconds) between scanning for changes", type=int)
    edit_folder_parser.add_argument('--minfree', '-m', metavar='PERCENT', type=int,
            help='percentage of space that should be available on the disk this folder resides')
    edit_folder_parser.add_argument('--type', '-t', metavar='TYPE', dest='folder_type',
            help='readonly or readwrite', choices=['readonly', 'readwrite'])
    edit_folder_parser.add_argument('--order', '-o', metavar='ORDER',
            help='see the Syncthing documentation for all options',
            choices=['random', 'alphabetic', 'smallestFirst', 'largestFirst',
                     'oldestFirst', 'newestFirst'])
    edit_folder_parser.add_argument('--ignore-permissions', action='store_true',
            help='ignore file permissions. Normally used on non-Unix filesystems')
    edit_folder_parser.add_argument('--sync-permissions', action='store_true',
            help='turn on syncing file permissions.')

    folder_versioning_parser = folder_subparsers.add_parser('versioning',
            help="configure file versioning")
    folder_versioning_parser.add_argument('folder', metavar='FOLDER', help="the folder to modify")
    folder_versioning_subparsers = folder_versioning_parser.add_subparsers(dest='versionparser_name',
            metavar='TYPE')
    trashcan_parser = folder_versioning_subparsers.add_parser('trashcan', help="move deleted files to .stversions")
    trashcan_parser.add_argument('--cleanout', default='0', help="number of days to keep files in trash", type=int)
    simple_parser = folder_versioning_subparsers.add_parser('simple', help="keep old versions of files in .stversions")
    simple_parser.add_argument('--versions', default='5', help="the number of versions to keep", type=int)
    staggered_parser = folder_versioning_subparsers.add_parser('staggered', help="specify a maximum age for versions")
    staggered_parser.add_argument('--maxage', metavar='MAXAGE', default='365',
            help="the maximum time to keep a version, in days, 0=forever", type=int)
    staggered_parser.add_argument('--path', metavar='PATH', default='', help="a custom path for storing versions")
    external_parser = folder_versioning_subparsers.add_parser('external', help="use a custom command for versioning")
    external_parser.add_argument('command', metavar='COMMAND', help='the command to run')
    noversioning_parser = folder_versioning_subparsers.add_parser('none', help="turn off versioning")

    folder_info_parser = folder_subparsers.add_parser('info', help='show detailed information about a folder')
    folder_info_parser.add_argument('folder', metavar='FOLDER', help='the folder name or label')

    list_folder_parser = folder_subparsers.add_parser('list', help='show a list of configured folders')

    return parser.parse_args()


def configure(configfile, apikey, hostname, port, name, default):
    config = configparser.ConfigParser()
    configfile = os.path.expandvars(configfile)
    if not name:
        name = hostname
    # Initialization of a config file
    if not os.path.exists(configfile):
        try:
            os.makedirs(os.path.dirname(configfile), exist_ok=True)
        except OSError:
            raise SyncthingManagerError("Couldn't create a path to " + configfile)
        config['DEFAULT'] = {}
        config['DEFAULT']['Name'] = name
    if not apikey:
        try:
            stconfigfile = os.path.expandvars(__DEFAULT_ST_CONFIG_LOCATION__)
            stconfig = parse(stconfigfile)
            root = stconfig.getroot()
            gui = root.find('gui')
            apikey = gui.find('apikey').text
        except FileNotFoundError:
            raise SyncthingManagerError("Autoconfiguration failed. Please "
                    "specify the API key manually.")
        except AttributeError:
            raise SyncthingManagerError("Autoconfiguration failed. Please "
                    "specify the API key manually.")
    config.read(configfile)
    config[name] = {}
    config[name]['APIkey'] = apikey
    config[name]['Hostname'] = hostname
    config[name]['Port'] = str(port)
    if default:
        config['DEFAULT']['Name'] = name
    try:
        with open(configfile, 'w') as cfg:
            config.write(cfg)
    except OSError:
        raise SyncthingManagerError("Couldn't write to the config file " + configfile)


def getAPIInfo(configfile, name='DEFAULT'):
    if not os.path.exists(os.path.expandvars(configfile)):
        raise SyncthingManagerError(configfile + " doesn't appear to be a valid path. Exiting.")
    config = configparser.ConfigParser()
    config.read(os.path.expandvars(configfile))
    if name == 'DEFAULT':
        return config[config['DEFAULT']['Name']]
    try:
        return config[name]
    except KeyError:
        raise SyncthingManagerError("The Syncthing daemon specified"
                " is not configured.")


def main():
    try:
        args = arguments()
        if args.subparser_name == 'configure':
            configure(args.config, args.apikey, args.hostname, args.port,
                    args.name, args.default)
            sys.exit(0)
        if not getAPIInfo(args.config, args.config_device):
            raise SyncthingManagerError("No Syncthing daemon is configured. Use "
                "stman configure apikey to initialize a configuration (apikey"
                " is in the syncthing settings and config.xml)")
        APIInfo = getAPIInfo(args.config, args.config_device)
        st = SyncthingManager(APIInfo['APIkey'], APIInfo['Hostname'], APIInfo['Port'])
        if args.subparser_name == 'device':
            if args.deviceparser_name == 'add':
                st.add_device(args.deviceID, args.name, args.address,
                        args.dynamic, args.introducer)
            elif args.deviceparser_name == 'remove':
                st.remove_device(args.device)
            elif args.deviceparser_name == 'info':
                st._print_device_info(args.device)
            elif args.deviceparser_name == 'list':
                st._device_list()
            elif args.deviceparser_name == 'edit':
                if args.name:
                    st.device_change_name(args.device, args.name)
                if args.introducer:
                    st.edit_device(args.device, 'introducer', True)
                if args.introducer_off:
                    st.edit_device(args.device, 'introducer', False)
                if args.add_address:
                    st.device_add_address(args.device, args.add_address)
                if args.remove_address:
                    st.device_remove_address(args.device, args.remove_address)
        elif args.subparser_name == 'daemon':
            if args.pause:
                st.daemon_pause(args.pause)
            if args.resume:
                st.daemon_resume(args.resume)
#            if args.pause_all:
#                st.daemon_pause('')
#            if args.resume_all:
#                st.daemon_resume('')
        elif args.subparser_name == 'folder':
            if args.folderparser_name == 'add':
                st.add_folder(args.path, args.folderID, args.label,
                        args.foldertype, args.rescan_interval)
            elif args.folderparser_name == 'remove':
                st.remove_folder(args.folder)
            elif args.folderparser_name == 'share':
                st.share_folder(args.folder, args.device)
            elif args.folderparser_name == 'unshare':
                st.unshare_folder(args.folder, args.device)
            elif args.folderparser_name == 'edit':
                if args.label:
                    st.folder_set_label(args.folder, args.label)
                if args.rescan:
                    st.folder_set_rescan(args.folder, args.rescan)
                if args.minfree:
                    st.folder_set_minfree(args.folder, args.minfree)
                if args.folder_type:
                    st.folder_set_type(args.folder, args.folder_type)
                if args.order:
                    st.folder_set_order(args.folder, args.order)
                if args.ignore_permissions:
                    st.folder_set_ignore_perms(args.folder, args.ignore_permissions)
                if args.sync_permissions:
                    st.folder_set_ignore_perms(args.folder, False)
            elif args.folderparser_name == 'versioning':
                if args.versionparser_name == 'trashcan':
                    st.folder_setup_versioning_trashcan(args.folder, args.cleanout)
                elif args.versionparser_name == 'simple':
                    st.folder_setup_versioning_simple(args.folder, args.versions)
                elif args.versionparser_name == 'staggered':
                    st.folder_setup_versioning_staggered(args.folder, args.maxage, args.path)
                elif args.versionparser_name == 'external':
                    st.folder_setup_versioning_external(args.folder, args.command)
                elif args.versionparser_name == 'none':
                    st.folder_setup_versioning_none(args.folder)
            elif args.folderparser_name == 'info':
                st._print_folder_info(args.folder)
            elif args.folderparser_name == 'list':
                st._folder_list()
    except SyncthingError as err:
        print(err)
        sys.exit(1)
    except SyncthingManagerError as err:
        print(err)
        sys.exit(1)


if __name__ == '__main__':
    main()
