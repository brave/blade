# Changelog

## [0.3] - 2025-07-23

- Add support for downsampling the data collected by Monsoon through the `--granularity` argument.
- Add support for Parquet output format using the `--format parquet` argument for improved performance with large datasets.
- Remove support for deprecated TLS versions 1.0 and 1.1.
- Convert time into context-based constants, at `constants.py`.
- Better handle mitmproxy errors, e.g., when the certificate is not found.
- Better handle device power-off to avoid data corruption (Android only for now).
- Fix issues with GPIO control in latest update of Raspberry Pi OS.
- This version supports the performance evaluation of Brave Android, reported at [Brave for Android continues to outperform other browsers in speed and performance, based on recent tests](https://brave.com/blog/brave-android-one-eight-zero-plus-performance/).


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
- Add remote control support for the device, available only on Android.


## [0.1] - 2024-07-19

- First public release of BLaDE infrastructure.
- This version supports our paper [MELT: Mobile Evaluation of Language Transformers](https://github.com/brave-experiments/MELT-public).
