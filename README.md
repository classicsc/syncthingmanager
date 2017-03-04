# syncthingmanager
A command line tool for the Syncthing API. Designed to make setting up remote servers easier.
(and for users who prefer the cli)

## Installation and configuration
###Requirements
- Python 3.4 or later
- setuptools and pip
- Syncthing 0.14.19 or later

Make sure you have setuptools installed, clone the repository, and run 
`python3 setup.py install`

The configuration must be initialized with the Syncthing API key.
Usually this can be done automatically:
`stman configure`. If that doesn't work, get the API key from the GUI 
or config.xml (in Syncthing's config directory), then run `stman configure apikey`.

### Configuration syntax
If your Syncthing GUI/API is on a non-standard port, or not on localhost, 
you will need to configure it manually. By default, `stman` will look for 
settings at `~/.config/syncthingmanager/syncthingmanager.conf`. 
A sample syncthingmanager.conf follows:

```
[DEFAULT]
name = localhost

[localhost]
apikey = MafkDvpagX5J6oMzxm9HwDSXJPSQKPFS
hostname = localhost
port = 8384

[remote-device]
apikey = h9mifaKwDq3SSPPmgUuDjsrivFg3dtkK
hostname = some-host
port = 9001
```

In this example, my default device is the one at localhost:8384. If I wanted 
to send a command to the one at some-host:9001, it would look like 
`stman --device remote-device ...`

## Usage
```
$ stman device list
$HOME/.config/syncthingmanager/syncthingmanager.conf doesn't appear to be a valid path. Exiting.
# Autoconfiguration
$ stman configure
# List configured devices
$ stman device list
syncthingmanager-test     This Device
    ID:     LYAB7ZG-XDVMAVM-OUZ7EAB-5N3UVWY-DXTFRJ4-U2MTHGQ-7TIBRJE-PC56BQ6

another-device     Connected
    At:     # Address removed
    Folders:    dotest
    ID:     H2AJWNR-5VYNWKM-PS2L2EE-QJYBG2U-3IFN5XM-EKSIIKF-NVLAG2E-KIQE4AE
# List configured folders
$ stman folder list
Default Folder
    Shared With:  
    Folder ID:  default
    Folder Path:    /home/syncthing/Sync/

do-test
    Shared With:  another-device
    Folder ID:  dotest
    Folder Path:    /home/syncthing/stman-test/
# Adding a device
$ stman device add MFZWI3D-BONSGYC-YLTMRWG-C43ENR5-QXGZDMM-FZWI3DP-BONSGYY-LTMRWAD -n yet-another-device -i
 
$ stman device list
syncthingmanager-test     This Device
    ID:     LYAB7ZG-XDVMAVM-OUZ7EAB-5N3UVWY-DXTFRJ4-U2MTHGQ-7TIBRJE-PC56BQ6

$ stman device add MFZWI3D-BONSGYC-YLTMRWG-C43ENR5-QXGZDMM-FZWI3DP-BONSGYY-LTMRWAD -n yet-another-device -i

$ stman device list
syncthingmanager-test     This Device
    ID:     LYAB7ZG-XDVMAVM-OUZ7EAB-5N3UVWY-DXTFRJ4-U2MTHGQ-7TIBRJE-PC56BQ6

sam-thinker     Connected
    At:     104.32.133.79:60249
    Folders:    dotest
    ID:     H2AJWNR-5VYNWKM-PS2L2EE-QJYBG2U-3IFN5XM-EKSIIKF-NVLAG2E-KIQE4AE

yet-another-device     Not Connected
    Folders:    
    ID:     MFZWI3D-BONSGYC-YLTMRWG-C43ENR5-QXGZDMM-FZWI3DP-BONSGYY-LTMRWAD
# Share a folder with a device
$ stman folder share dotest yet-another-device
$ stman folder list
Default Folder
    Shared With:  
    Folder ID:  default
    Folder Path:    /home/syncthing/Sync/

do-test
    Shared With:  another-device, yet-another-device
    Folder ID:  dotest
    Folder Path:    /home/syncthing/stman-test/
# Configure and view advanced options
$ stman folder versioning dotest simple --versions 15
$ stman folder edit dotest -r 70
$ stman folder info dotest
do-test
    Shared With:  another-device, yet-another-device
    Folder ID:  dotest
    Folder Path:    /home/syncthing/stman-test/                
    Rescan Interval:    70
    File Pull Order:  alphabetic
    Versioning:       simple
    Keep Versions:      15
```

Other commands are documented in `stman -h`, `stman command -h`, and so on.


## Notes
- On Windows, cmd.exe will print funny characters in place of colors.
PowerShell works fine.
- Some information shown in the GUI requires use of the Events API, which
isn't part of python-syncthing. I plan on creating Python bindings for it
and using the results, but haven't started yet.
- I chose to have the device list output be online first instead of 
alphabetical.
