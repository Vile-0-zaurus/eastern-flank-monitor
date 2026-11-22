# Deploy notes

This is not a public site. Live monitoring stays off until a later assignment turns it on.

## Service path

The user service files need an absolute path. systemd does not expand a tilde. `%h` means the home directory of the user who runs the service.

Both `systemd/user/daily-collect.service` and `systemd/user/efm-now-download.service` set:

`EFM_ROOT=%h/Projects/eastern-flank-monitor`

That is the default checkout. If the repo lives somewhere else, override the variable and reload:

1. `systemctl --user edit daily-collect.service`
2. Add `Environment=EFM_ROOT=/path/to/eastern-flank-monitor` under `[Service]`.
3. `systemctl --user daemon-reload`

The installed copies under the user systemd folder are separate from these repo files. Copy the unit again after this change if you want the running unit to match.
