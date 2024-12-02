#!/bin/sh

# Adds script directories
pathadd PATH ${HOME}/.scripts
pathadd PATH ${HOME}/.scripts-local > /dev/null

# Adds additional scripts.
pathadd PATH ${HOME}/.local/bin > /dev/null
pathadd PATH ${HOME}/.third-party/bin

# Golang
export GOPATH=${HOME}/.go

# Cleans up paths
pathclean PATH
pathclean CPATH
pathclean LIBRARY_PATH
pathclean LD_LIBRARY_PATH
pathclean C_INCLUDE_PATH
pathclean CPLUS_INCLUDE_PATH
