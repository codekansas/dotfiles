#!/bin/sh

# UV environments
if [[ -d ${HOME}/.virtualenvs ]] && [[ ! -z $(ls -1 ${HOME}/.virtualenvs/ 2>/dev/null) ]]; then
    ls -1 ${HOME}/.virtualenvs/ | while read line; do echo -n -e "[\033[1;33m$(basename $line)\033[0m] "; done
    echo -n -e "\n"
fi

# Conda environments
if [[ -f ${HOME}/.conda/environments.txt ]] && [[ ! -z $(grep '[^[:space:]]' "${HOME}/.conda/environments.txt")  ]]; then
    cat ${HOME}/.conda/environments.txt | sort | while read line; do echo -n -e "[\033[1;32m$(basename $line)\033[0m] "; done
    echo -n -e "\n"
fi

# TMUX active sessions
if [[ ! -z $(tmux ls 2>/dev/null) ]]; then
    tmux ls 2>/dev/null | while read line; do echo -n -e "[\033[1;35m$(echo $line | cut -d: -f1)\033[0m] "; done
    echo -n -e "\n"
fi
