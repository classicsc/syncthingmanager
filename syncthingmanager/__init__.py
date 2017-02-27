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

# Put globals here
__NAME__ = 'syncthingmanager'
__VERSION__ = '0.1.0'
__DEFAULT_CONFIG_LOCATION__ = '~/.config/syncthingmanager/syncthingmanager.conf'

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
        else:
            for index, device in enumerate(config['devices']):
                if device_id == device['deviceID']:
                    deviceindex = index
                    device_name = device['name']
            for folder in config['folders']:
                for d in folder['devices']:
                    if device['deviceID'] == d['deviceID']: 
                        folders.append(folder['id'])
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

    def add_device(self, device_id, name='', address='', dynamic=False, 
            introducer=False):
        """ Adds a device to the configuration and sets the configuration.
        Args:
            device_id (str): The device ID to be added.
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
            config['devices'].append(dict({'deviceID': info['id'], 'name': name,
                'addresses': addresses, 'compression': 'metadata', 
                'certName': '', 'introducer': introducer}))
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
            except pathlib.FileNotFoundError:
                raise SyncthingManagerError("There was a problem with the path \
                        entered: " + path)
            folder = dict({'id': folderid, 'label': label, 'path': str(path),
                'type': foldertype, 'rescanIntervalS': rescan, 'fsync': True, 
                'autoNormalize': True, 'maxConflicts': 10, 'pullerSleepS': 0})
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
                    + "of a configured folder.")
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
                    + "of a configured folder.")
        deviceinfo = self.device_info(devicestr)
        if deviceinfo['index'] == None:
            raise SyncthingManagerError(devicestr + " is not a configured" 
                     + " device name or ID")
        for device in info['devices']:
            if device['deviceID'] == deviceinfo['id']:
                raise SyncthingManagerError(devicestr + " is already " 
                        + "associated with " + folderstr)
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
            raise SyncthingManagerError(folderstr + " is not the ID or label \
                    of a configured folder.")
        deviceinfo = self.device_info(devicestr)
        if deviceinfo['index'] == None:
            raise SyncthingManagerError(devicestr + " is not a configured \
                    device name or ID")
        config = self.system.config()
        for index, device in enumerate(info['devices']):
            if device['deviceID'] == deviceinfo['id']:
                del info['devices'][index]
                config['folders'][info['index']]['devices'] = info['devices']
                self.system.set_config(config)
                return
        raise SyncthingManagerError(devicestr + " is not associated with "
                + folderstr)

    def _device_list(self):
        """Prints out a formatted list of devices and their state from the
            active configuration."""
        config = self.system.config()
        connections = self.system.connections()['connections']
        connected = filter(lambda x: connections[x['deviceID']]['connected'],
                config['devices'])
        not_connected = filter(lambda x: x not in connected, config['devices'])
        for device in connected:
            address = connections[device['deviceID']]['address']
            folders = self.device_info(device['deviceID'])['folders']
            #TODO Figure out the sync percentage per device. Probably from
            # events API.
            #if complete == 100:
            #    sync = '\tUp to Date'
            #else:
            #    sync = '\tSyncing (' + str(complete) + '%)'
            sync = '\tConnected'
            print(device['name'] + OKGREEN + sync + ENDC)
            print('\tAt:\t' + address)
            print('\tFolders:\t' + ','.join(map(str,folders)))

        for device in not_connected:
            folders = self.device_info(device['deviceID'])['folders']
            print(device['name'] + FAIL + ' Not Connected' + ENDC)
            print('\tFolders:\t' + ','.join(map(str,folders)))

    def _folder_list(self):
        """Prints out a formatted list of folders from the configuration."""
        config = self.system.config()
        for folder in config['folders']:
            devices = []
            for device in folder['devices']:
                name = self.device_info(device['deviceID'])['name']
                devices.append(name)
            if folder['label'] == '':
                folderstr = folder['id']
            else:
                folderstr = folder['label']
            print(folderstr)
            print('\tConnected devices: ' + ','.join(map(str, devices)))



def arguments():
    parser = ArgumentParser()
    parser.add_argument('--config', '-c', default=__DEFAULT_CONFIG_LOCATION__,
            help="stman configuration file")
    base_subparsers = parser.add_subparsers(dest='subparser_name', 
            metavar='action')
    base_subparsers.required = True

    configuration_parser = base_subparsers.add_parser('configure',
            help="configure stman. If the configuration file specified in " + 
            "-c (or the default) does not exist, it will be created. To edit an " + 
            "existing configuration, specify all options again.")
    configuration_parser.add_argument('APIkey', help="the Syncthing API key, "
            + "found in the GUI or config.xml")
    configuration_parser.add_argument('--hostname', '-a', default='localhost',
            help="the hostname to use. default localhost.")
    configuration_parser.add_argument('--port', '-p', default='8384',
            help="the port to use. Default 8384")
    configuration_parser.add_argument('--name', '-n',
            help="what to call this device. Defaults to the hostname.")
    configuration_parser.add_argument('--default', action='store_true',
            help="make this device the default.")

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

    list_device_parser = device_subparsers.add_parser('list',
            help="prints a list of devices and some information")

    remove_device_parser = device_subparsers.add_parser('remove',
            help="remove a device")
    remove_device_parser.add_argument('device', metavar='DEVICE', help="the name or ID to be removed")

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
            help="'readwrite' or 'readonly'. Default readwrite")
    add_folder_parser.add_argument('--rescan-interval', '-r', default=60,
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
    unshare_folder_parser.add_argument('device', metavar='DEVICE', help='the device ID or label')

    list_folder_parser = folder_subparsers.add_parser('list', help='prints a list of configured folders')

    return parser.parse_args()

def configure(configfile, apikey, hostname, port, name, default):
    config = configparser.ConfigParser()
    configfile = os.path.expanduser(configfile)
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
    if not os.path.exists(os.path.expanduser(configfile)):
        raise SyncthingManagerError(configfile + " doesn't appear to be a valid path. Exiting.")
    config = configparser.ConfigParser()
    config.read(os.path.expanduser(configfile))
    if name == 'DEFAULT':
        return config[config['DEFAULT']['Name']]
    try:
        return config[name]
    except KeyError:
        raise SyncthingManagerError("The Syncthing daemon specified"
                + " is not configured.")

def main():
    try:
        args = arguments()
        if args.subparser_name == 'configure':
            configure(args.config, args.APIkey, args.hostname, args.port, 
                    args.name, args.default)
            sys.exit(0)
        if not getAPIInfo(args.config):
            raise SyncthingManagerError("No Syncthing daemon is configured. Use "
                + "stman configure apikey to initialize a configuration (apikey" + 
                " is in the syncthing settings and config.xml)")
        APIInfo = getAPIInfo(args.config)
        st = SyncthingManager(APIInfo['APIkey'], APIInfo['Hostname'], APIInfo['Port'])
        if args.subparser_name == 'device':
            if args.deviceparser_name == 'add':
                st.add_device(args.deviceID, args.name, args.address,
                        args.dynamic, args.introducer)
            elif args.deviceparser_name == 'remove':
                st.remove_device(args.device)
            elif args.deviceparser_name == 'list':
                st._device_list()
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
