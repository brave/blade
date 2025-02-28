# Changelog

## [0.2] - 2025-02-27

- Refactor the codebase to use it as a submodule in other projects.
- Remove support for `-ee` argument.
- Remove `experiments` folder.
- Support `--auto-recharge` argument to automatically recharge the battery of the device during experiments.
- Remove unused libs and scripts, not relevant to core BLaDE infrastructure.
- Convert wait times into constants.
- Support latest Raspberry Pi 5 and Raspberry Pi OS 12 (Bookworm).
- `pid` files are now saved into a global `.pid_files` folder
- Add support for memory monitoring per app.
- Support local proxy for dynamically injecting custom JavaScript.
- Updated documentation and list of optional but recommended OS configuration settings.
- Add a logger that by default logs to the stdout, and with flag `--log-output` it adds a log.txt file to the output directory. 
- Replace parameter `-d` to be a positional parameter which is required, except when running `-h`, `-ld` or `--list-devices`. 
- Add support for remote control for the device. Only available for Android devices.

## [0.1] - 2024-07-19

- First public release of BLaDE infrastructure.
- This version supports our paper [MELT: Mobile Evaluation of Language Transformers](https://github.com/brave-experiments/MELT-public).
