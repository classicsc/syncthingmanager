# syncthingmanager
A command line tool for the Syncthing API. Designed to make setting up remote servers easier.
(and for users who prefer the cli)

## Features
- Adding and removing devices
- Adding and removing folders
- Sharing folders
- More to come...

## Usage
The first time you use `stman`, you must give it the Syncthing API key.
This can be found in the GUI or in the file `~/.config/syncthing/config.xml`.
Then run `stman configure APIKEY`.

All commands are documented in `stman -h`.

## TODO
- Untested on non-Linux platforms
- More commands should be implemented, for changing the settings of existing
folders and devices.
- Should be able to find the API key automatically in most cases
- Output of the device and folder listings could be prettier and more complete.
- Tests are ugly and minimal, make them more systematic and complete.
- You tell me! Open an issue and/or PR if you think a new command would be 
useful, or something unexpected happens.
