# dotfiles

Repo for managing my dotfiles across several environments.

## Installation

```sh
git clone git@github.com:codekansas/dotfiles.git && cd dotfiles && ./install
```

`./install` defaults to the `local` profile and installs everything. Use `./install devbox` for shared development machines where local scheduled jobs and package-manager changes should be skipped.

## Related

- I borrowed a lot of this repo from [here](https://github.com/mikejqzhang/dotfiles)
- Installation is handled by the first-party Python package in this repo.

## Documentation

Here are some of the additional commands in these dotfiles, besides the housekeeping-type improvements.

### prof

Profile directory (useful for finding large files):

```bash
prof (<dir-name>)
```

### mkcd

Make directory, then `cd` to that directory

```bash
mkcd <dir-name>
```

### gdrive

Download file from Google drive:

```bash
gdrive <google-fid> <output-path>
```

### topc

Filter `top` for process name regex:

```bash
topc <regex>
```

### conda

Edit Conda environment variables:

```bash
cvars (rm {r}) (rm-activate {ra}) (rm-deactivate {rd}) (activate {a}) (deactivate {d})
```

Activate Conda environment (alias for `conda activate`, with tab completion):

```bash
cenv <env-name>
```

### tmp-script

Create a new temporary script:

```bash
tinit <script-name>
```

Edit a script (with tab completion):

```bash
tedit <script-name>
```

Run a temporary script (with tab completion):

```bash
trun <script-name>
```

Delete a script (with tab completion):

```bash
tdelete <script-name>
```

### nvidia

Track NVIDIA GPU usage:

```bash
smi
```

### tmux

Create or attach to a `tmux` session named after the current directory:

```bash
tms
```

Create or attach to a named `tmux` session:

```bash
tm <name>
```

### ssh

Add this in your `~/.ssh/config` file to prevent having to re-authenticate when SSH'ing (useful for 2FA):

```bash
Include config.d/base
```

By default, Jupyter notebooks will be served on port 16012. Therefore, it's a good idea to add this port forwarding to your SSH config file:

```bash
LocalForward 16012 localhost:16012
```

### make

Build a file, and if make succeeds, run it (currently NVCC and C / C++). Useful for programming competitions, test scripts, etc.

```bash
brun <fname> (runtime-args)
```
