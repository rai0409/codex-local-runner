# Prompt659B Summary

Status: success.

Implemented controlled Windows/WSL reachability for the ChatGPT Runner Bridge.

Server changes:

- Default bind remains `127.0.0.1`.
- `localhost` and `127.0.0.1` remain allowed by default.
- Private IPv4 bind addresses in `10.0.0.0/8`, `172.16.0.0/12`, and
  `192.168.0.0/16` are allowed only with `--allow-private-host-bind`.
- `0.0.0.0`, public IPs, arbitrary hostnames, empty hosts, and IPv6 hosts are
  rejected.
- CLI now includes `diagnose-windows-wsl-reachability`.

Extension changes:

- Default bridge URL remains `http://127.0.0.1:8765`.
- Bridge URL is configurable via an options page backed by `chrome.storage.local`.
- Configured bridge URLs must be HTTP loopback or private IPv4 URLs.
- Credential-bearing URLs, public URLs, wildcard host URLs, paths, queries, and
  fragments are rejected.
- Extension health check support was added.

Documentation:

- README now includes the exact Windows/WSL workflow:
  `hostname -I | awk '{print $1}'`, private-bind server command, PowerShell
  health check, extension URL setting, ChatGPT tab reload, and click flow.

Validation:

- Focused Prompt659B tests passed.
- Full requested regression suite passed: 178 tests.

No browser live run was performed or claimed.
