#!/bin/sh

# Show an error if this fails for some reason.
# err_report() {
#     echo "Error on line $1"
# }
# trap 'err_report $LINENO' ERR

# C++ flags for programming competitions.
# export CXXFLAGS="-Wall -Wextra -O2 -pedantic -std=c++11"

# -------------
# Color aliases
# -------------

red() {
    tput setaf 1
}
green() {
    tput setaf 2
}
yellow() {
    tput setaf 3
}
blue() {
    tput setaf 4
}
magenta() {
    tput setaf 5
}
cyan() {
    tput setaf 6
}
white() {
    tput setaf 7
}
no_color() {
    tput sgr 0
}

# -----------
# OS-Specific
# -----------

case $OSTYPE in
    "darwin"*)
        alias ls='ls -G'

        export SLURM_LOG_DIR=${HOME}/Experiments/.Slurm
        export LOG_DIR=${HOME}/Experiments/Logs
        export EVAL_DIR=${HOME}/Experiments/Evaluation
        export DATA_DIR=${HOME}/Experiments/Data
        export DATA_CACHE_DIR=${DATA_DIR}/.Cache
        export MODEL_DIR=${HOME}/Experiments/Models
        export STAGE_DIR=${HOME}/Experiments/Stage
        export RUN_DIR=${LOG_DIR}/today
        export EVAL_RUN_DIR=${EVAL_DIR}/today
        ;;
    "linux-gnu"*)
        alias ls='ls --color=always'

        export SLURM_LOG_DIR=${HOME}/Experiments/Slurm
        export LOG_DIR=${HOME}/Experiments/Logs
        export EVAL_DIR=${HOME}/Experiments/Evaluation
        export DATA_DIR=${HOME}/Experiments/Data
        export DATA_CACHE_DIR=${DATA_DIR}/.Cache
        export MODEL_DIR=${HOME}/Experiments/Models
        export STAGE_DIR=${HOME}/Experiments/Stage
        export RUN_DIR=${LOG_DIR}/today
        export EVAL_RUN_DIR=${EVAL_DIR}/today
        ;;
    *)
        echo "OS type not supported: '$OSTYPE'"
        return
        ;;
esac

ddate() {
    if [[ $# -lt 1 ]]; then
        echo "Usage: ddate <num-dates-past> (other-args)"
        return 1
    fi
    local delta=$1
    shift
    if [[ $OSTYPE == "darwin"* ]]; then
        date -v -${delta}d $@
    else
        date --date "${delta} days ago" $@
    fi
    return 0
}

# Some extra bit that seems to be necessary for VSCode.
if [ -d /etc/profile.d ]; then
    for i in /etc/profile.d/*.sh; do
        if [ -r $i ]; then
            . $i
        fi
    done
    unset i
fi

# grep
alias cgrep='grep --color=always'

# ls
alias ll='ls -lah'
alias la='ls -A'

# protect against overwriting
alias cp='cp -i'
alias mv='mv -i'

# clear
alias cl='clear'
alias reload='exec $SHELL'

# nvidia
alias smi='nvidia-smi --query-gpu=index,name,utilization.gpu,utilization.memory,memory.total,memory.used --format=csv -l 1'
alias smiwho="ps -up \$(nvidia-smi -q -x | grep pid | sed -e 's/<pid>//g' -e 's/<\/pid>//g' -e 's/^[[:space:]]*//')"

# cursor
alias update-cursor='brew install --cask --force cursor'

# time
alias today='date +"%Y-%m-%d'
alias now='date +"%T"'

# paths
alias rp='realpath'

# sortable time format
export SLURM_TIME_FORMAT='%D (%a) %T'

# kill stopped jobs
alias kill-stopped='kill -9 `jobs -ps`'

# kill python jobs
alias killall-py='killall -u ${USER} -n python'

# show a warning if startup takes longer than this
export SLOW_STARTUP_WARNING_MS=1000

qq() {
    local strings=$(
        squeue --format="%.8i %.12P %30j %.10T %.12M %100N" $@ \
        | awk '{$6=substr($6, length($6)-35)}1' \
        | rev \
        | awk '{$1=substr($1, length($1)-35)}1' \
        | rev
    )
    echo "$strings" | column -t
}

alias qm='qq --me'

spartme() {
    if [[ $# -ne 1 ]]; then
        echo "Changes all existing jobs to a partition"
        echo "Usage: spartme <partition>"
    fi
    partition=$1
    jobids=$(squeue -u $USER -h -t PD -o %i)
    numjobs=$(echo $jobids | wc -w)
    echo "Changing $numjobs jobs to $partition partition"
    for i in ${jobids[@]}; do
        scontrol update jobid=$i partition=$partition
    done
}

portps() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: port-ps <port-num>"
        return 1
    else
        lsof -nP "-i4TCP:$1"
        return 0
    fi
}

sdate() {
    if [[ $# -ne 1  ]]; then
        echo "Usage: sdate <time-string>"
        return 1
    else
        echo $(date +"%Y-%m-%d-%T" -d "$1")
        return 0
    fi
}

shelp() {
    echo "Example slurm commands:

    $(blue)shist$(no_color) --starttime=\$(sdate '$(green)7 days ago$(no_color)') --endtime=\$(sdate '$(red)1 hour ago$(no_color)')
    $(blue)shist$(no_color) --starttime=\$(sdate '$(green)24 hours ago$(no_color)') --endtime=\$(sdate '$(red)1 hour ago$(no_color)')
    $(blue)shist$(no_color) --starttime=\$(sdate '$(green)1 hour ago$(no_color)') --endtime=\$(sdate '$(red)now$(no_color)')
"
}

shist() {
    sacct --format='Start%25,End%25,JobID,JobName%30,Partition,State%20' --user $USER $@ | awk 'NR<3{print $0;next}{print$0| "sort -r"}'| less
}

slog() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: slog <job-id>"
        return 1
    fi
    local job_id=$1; shift
    echo $(slurm-get-job-path $job_id --silent)
}

plog() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: plog <process-id>"
        return 1
    fi
    local process_id=$1; shift
    echo $(log-dir-from-proc-id $process_id --silent)
}

sjson() {
    if [[ $# -ne 2 ]]; then
        echo "Usage: sjson <job-id> <json-field>"
        return 1
    fi
    local log_dir=$(slog $1)
    local json_field=$2
    if [[ -n $log_dir ]]; then
        jq -r $json_field ${log_dir}/slurm_info.json
    else
        echo "Failed to get log directory for job ID $1"
        return 1
    fi
}

sjsons() {
    if [[ $# -lt 1 ]]; then
        echo "Usage: sjsons <json-field> (<job-id> ...)"
        return 1
    fi
    local json_field=$1; shift

    local job_ids=()
    if [[ $# -eq 0 ]]; then
        while IFS= read -r line; do
            job_ids+=("$line")
        done < <(squeue -u "$USER" -h -t R -o %i)
    else
        job_ids=("$@")
    fi

    for job_id in ${job_ids[@]}; do
        sjson $job_id $json_field
    done
}

scomments() {
    sjsons '[.[-1].job_id, .[-1].job.task_key, .[-1].comment] | @json' $@
}

scommentsmediawiki() {
    if [[ $# -ne 0 ]] && [[ $# -ne 1 ]]; then
        echo "Usage: scommentsmediawiki (<trg-task>)"
        return 1
    fi
    local trg_task=$1; shift
    echo "{| class="wikitable""
    echo "! Job ID"
    if [[ -z "$trg_task" ]]; then
        echo "! Task"
    fi
    echo "! Comment"
    job_ids=()
    while IFS= read -r line; do
        local job_id=$(echo $line | jq -r '.[0]')
        local task=$(echo $line | jq -r '.[1]')
        local comment=$(echo $line | jq -r '.[2]')
        if [[ "$trg_task" == "" ]]; then
            echo "|-"
            echo "| $job_id"
            echo "| $task"
            echo "| $comment"
            job_ids+=("$job_id")
        elif [[ "$trg_task" == "$task" ]]; then
            echo "|-"
            echo "| $job_id"
            echo "| $comment"
            job_ids+=("$job_id")
        fi
    done < <(scomments $@)
    echo "|}"
    echo ""
    echo '<syntaxhighlight lang="text">'
    echo "stbd ${job_ids[@]}"
    echo '</syntaxhighlight>'
}

sl() {
    local log_dir=$(slog $@)
    if [[ -n $log_dir ]]; then
        less +F ${log_dir}/slurm/*.slurm
    else
        echo "Failed to get log directory for job ID $1"
        return 1
    fi
}

st() {
    local log_dir=$(slog $@)
    if [[ -n $log_dir ]]; then
        for f in ${log_dir}/slurm/*.slurm; do
            echo "\n$(basename $f)\n"
            tail --lines 10 $f | sed 's/^/  /'
        done
    else
        echo "Failed to get log directory for job ID $1"
        return 1
    fi
}

stl() {
    st $@ | less
}

stbd() {
    local job_ids=()
    if [[ $# -eq 0 ]]; then
        while IFS= read -r line; do
            job_ids+=("$line")
        done < <(squeue -u "$USER" -h -t R -o %i)
    else
        job_ids=("$@")
    fi

    local tmp_tbd_dir=$(mktemp -d -t tbd-XXXXXXXX)
    local has_dir=0
    for job_id in ${job_ids[@]}; do
        local log_dir=$(slog $job_id)
        local tbd_root=${log_dir}/tensorboard/
        if [[ -d $tbd_root ]]; then
            echo "-> ${tbd_root}"
            ln -s ${tbd_root} ${tmp_tbd_dir}/${job_id}
            has_dir=1
        else
            echo "Failed to get tensorboard directory for job ID $job_id"
        fi
    done

    if [[ $has_dir -eq 0 ]]; then
        echo "No log directories found"
        return 1
    fi

    local cmd="tensorboard serve --logdir ${tmp_tbd_dir}"
    if [[ -n $TENSORBOARD_PORT ]]; then
        cmd="${cmd} --port ${TENSORBOARD_PORT}"
    fi
    if [[ $TENSORBOARD_BIND_ALL -eq 1 ]]; then
        cmd="${cmd} --bind_all"
    fi

    echo "Running '$cmd'"
    eval $cmd

    rm -r $tmp_tbd_dir
}

export GROUPED_TENSORBOARD_PORT=6005

gtbd() {
    local proc_ids=()
    if [[ $# -eq 0 ]]; then
        # Attempts to parse running jobs using Nvidia SMI.
        while IFS= read -r line; do
            proc_ids+=("$line")
        done < <(nvidia-smi --query-compute-apps=pid,name --format=csv | tail -n +2 | awk -F ',' '{print $1}')
    else
        proc_ids=("$@")
    fi

    local tmp_tbd_dir=$(mktemp -d -t tbd-XXXXXXXX)

    # For each path, find all subdirectories named `tensorboard` and link them to the tmp directory.
    local has_dir=0
    for proc_id in ${proc_ids[@]}; do
        local log_dir=$(plog $proc_id)
        local tbd_root=${log_dir}/tensorboard/
        if [[ -d "${tbd_root}" ]]; then
            echo "-> ${tbd_root}"
            ln -s "${tbd_root}" "${tmp_tbd_dir}/${proc_id}"
            has_dir=1
        else
            echo "Failed to get tensorboard directory for process ID $proc_id"
        fi
    done

    if [[ $has_dir -eq 0 ]]; then
        echo "No log directories found"
        return 1
    fi

    local cmd="tensorboard serve --logdir ${tmp_tbd_dir}"
    if [[ -n $GROUPED_TENSORBOARD_PORT ]]; then
        cmd="${cmd} --port ${GROUPED_TENSORBOARD_PORT}"
    fi
    if [[ $TENSORBOARD_BIND_ALL -eq 1 ]]; then
        cmd="${cmd} --bind_all"
    fi

    echo "Running '$cmd'"
    eval $cmd

    rm -r $tmp_tbd_dir
}

# speed test
speedtest() {
    echo "Runs speed test against remote server

    $(green)speedtest$(no_color) local <machine-name>  $(blue)# Run on the local machine$(no_color)
    $(green)speedtest$(no_color) remote                $(blue)# Run on the remote machine$(no_color)
"

    if [[ $# -eq 0 ]]; then
        echo "Mode required (must be one of [remote|local])"
        return 1
    fi

    local mode=$1
    shift

    case $mode in
        local)
            if [[ $# -lt 1 ]]; then
                echo "Must pass host name"
                return 1
            else
                machine_name=$1
                shift
                iperf -c $machine_name $@
            fi
            ;;
        remote)
            iperf -s $@
            ;;
        *)
            echo "Invalid mode: ${mode} (must be one of [remote|local])"
            return 1
            ;;
    esac

    return 0
}

# less
export LESS="-R"
alias lesc='LESSOPEN="|pygmentize -O style=emacs -g %s" less'
alias lesg='less ++G'  # Automatically jump to end

# python
export PYTHONHASHSEED=1337  # For making experiments repeatable
# export PYTHONSTARTUP="${HOME}/.python/startup.py"

# jupyter
alias jpn='USE_JUPYTER_CONF=1 jupyter notebook'
export JUPYTER_NOTEBOOK_PORT=${JUPYTER_NOTEBOOK_PORT:-44638}

# scikit-learn
export SCIKIT_LEARN_DATA=${DATA_DIR}/scikit-learn

# EC2 options
export ML_EC2_IMAGE_ID=ami-0d8efac6374295c8a
export ML_EC2_INSTANCE_TYPE=g4dn.xlarge
export ML_EC2_SECURITY_GROUP=model-training

clear-jpn() {
    local dir
    if [[ $# -eq 0 ]]; then
        dir=$(pwd)
    else
        dir=$1
    fi
    dir=$(realpath $dir)
    echo "Clearing all Jupyter notebooks in ${dir}"
    find . -type f -name "*.ipynb" -exec jupyter nbconvert --clear-output {} \;
}

# CUDA
export TORCH_CUDA_ARCH_LIST="6.0;6.1;6.2;7.0;7.5;8.0"

# Fixing vimrc colors inside tmux
export TERM=screen-256color

# Tensorboard flags.
export TENSORBOARD_BIND_ALL=1

# tensorboard
tbd() {
    local cmd
    local extra

    if [[ -n $TENSORBOARD_PORT ]] && [[ $# -ne 2 ]]; then
        extra="--port ${TENSORBOARD_PORT}"
    fi
    if [[ $TENSORBOARD_BIND_ALL -eq 1 ]]; then
        extra="--bind_all"
    fi

    if [[ $# -eq 0 ]]; then
        cmd="tensorboard serve --reload_interval 30 --logdir . ${extra}"
    elif [[ $# -eq 1 ]]; then
        cmd="tensorboard serve --reload_interval 30 --logdir $1 ${extra}"; shift
    elif [[ $# -eq 2 ]]; then
        cmd="tensorboard serve --reload_interval 30 --logdir $1 --port $2 ${extra}"; shift; shift
    else
        echo "Usage: tbd (<directory>) (<port>)"
    fi
    echo "Running '$cmd'"
    eval $cmd
}

# pwd without symlinks
alias pwd='pwd -P'

# zellij
alias zj='zellij'
export ZELLIJ_CONFIG_FILE=$(realpath $HOME/.config/zellij/config.kdl)

# tmux
# export TMUX_ATTACH_ARGS="-CC"
export TMUX_ATTACH_ARGS=""

tm() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: tm <session-name>"
        return 1
    fi

    local session_name=$1
    local session_exists=$(tmux list-sessions | grep -c $session_name)
    if [[ $session_exists -eq 0 ]]; then
        tmux new-session -d -s $session_name
        echo "Created session $session_name"
    fi
    tmux ${TMUX_ATTACH_ARGS} attach -t $session_name
    return 0
}

# filter top for process regex
topc() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: topc <regex>"
        return 1
    fi

    top -c -p $(pgrep -d',' -f $1)
    return 0
}

# profile directory
prof() {
    if [[ $# -ne 0 ]]; then
        DEPTH=$1
        shift
    else
        DEPTH=4
    fi

    du -h -d $DEPTH | sort -h
    return 0
}

# make directory and change to that directory
mkcd() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: mkcd <dir-name>"
        return 1
    fi

    mkdir $1
    cd $1
    return 0
}

# change to last directory alphabetically (useful for date folders)
cb() {
    local last_dir
    last_dir=$(\ls -1 | tail -1)
    echo "cd ${last_dir}"
    cd ${last_dir}
}

# kill vscode
__kill_vscode() {
    local nprocs=$(pgrep -u $USER -f vscode | wc -l | awk '{ print $1 }')
    echo "($1) Killing ${nprocs} processes"
    case $1 in
        dry)
            pgrep -u $USER -f vscode | xargs ps p
            ;;
        run)
            pkill -15 -u $USER -f vscode
            ;;
        * )
            echo "Unexpected or missing argument: $1"
            echo "Usage: vsc kill <run|dry>"
            return 1
            ;;
    esac
    return 0
}

# clean vscode (useful for when some extensions freeze up)
__clean_vscode() {
    local vscode_dirs
    vscode_dirs[0]=${HOME}/.vscode/
    vscode_dirs[1]=${HOME}/.vscode-insiders/
    vscode_dirs[2]=${HOME}/.vscode-server/
    vscode_dirs[3]=${HOME}/.vscode-server-insiders/
    vscode_dirs[4]=${HOME}/Library/Application\ Support/Code/
    vscode_dirs[5]=${HOME}/Library/Application\ Support/Code\ -\ Insiders/
    vscode_dirs[6]=${HOME}/.config/Code/
    vscode_dirs[7]=${HOME}/.config/Code\ -\ Insiders/
    for vscode_dir in ${vscode_dirs[@]}; do
        if [ -d $vscode_dir ]; then
            echo "($1) Removing $vscode_dir"
            case $1 in
                dry)
                    echo "SKIPPING ACTION"
                    ;;
                run)
                    rm -rf $vscode_dir
                    ;;
                *)
                    echo "Unexpected or missing argument: $1"
                    echo "Usage: vsc clean <run|dry>"
                    return 1
                    ;;
            esac
        fi
    done

    local num_tmp=$(find /tmp/ -maxdepth 1 -user $USER -name "*vscode*" 2> /dev/null | wc -l | awk '{ print $1 }')
    echo "($1) Removing $num_tmp temp files"

    case $1 in
        dry)
            echo "SKIPPING ACTION"
            ;;
        run)
            find /tmp/ -maxdepth 1 -user $USER -name "*vscode*" -exec rm -rf {} \; 2> /dev/null
            ;;
        *)
            echo "Unexpected or missing argument: $1"
            echo "Usage: vsc clean <run|dry>"
            return 1
            ;;
    esac

    return 0
}

__clean_cache_vscode() {
    local vscode_dirs
    vscode_dirs[0]=${HOME}/Library/Application\ Support/Code/
    vscode_dirs[1]=${HOME}/Library/Application\ Support/Code\ -\ Insiders/
    vscode_dirs[2]=${HOME}/.config/Code/
    vscode_dirs[3]=${HOME}/.config/Code\ -\ Insiders/
    for vscode_dir in ${vscode_dirs[@]}; do
        state_db=$vscode_dir/User/globalStorage/state.vscdb

        # Deletes cache of Python interpreters.
        if [ -d $state_db ]; then
            sqlite3 $state_db "DELETE FROM ItemTable WHERE key = 'ms-python.python';"
        fi
    done
}

vsc() {
    if [ $# -lt 1 ]; then
        echo "Usage: vsc <clean|kill>"
        return 1
    fi

    local cmd=$1
    shift

    case $cmd in
        clean)
            __clean_vscode $@
            ;;
        kill)
            __kill_vscode $@
            ;;
        *)
            echo "Usage: vsc <clean|kill>"
            return 1
            ;;
    esac
    return 0
}

# pgrep with tree (only in bash)
ppgrep() {
    pgrep "$@" | xargs --no-run-if-empty ps fp;
    return 0
}

# Shows process tree.
alias psme='pstree -p $(whoami)'

# ubuntu: combine apt update && upgrade
aptu() {
    apt update
    apt upgrade
    apt autoremove
}

# NVM
load-nvm() {
    unalias nvm 2> /dev/null
    unalias npm 2> /dev/null
    if [[ -d ~/.nvm ]]; then
        export NVM_DIR="$HOME/.nvm"
    elif [[ -d /opt/homebrew/opt/nvm ]]; then
        export NVM_DIR="/opt/homebrew/opt/nvm"
    fi
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
}
alias nvm='echo "Run load-nvm first"'
alias npm='echo "Run load-nvm first"'

# Ruby
load-ruby() {
    unalias rbenv 2> /dev/null
    unalias rvm 2> /dev/null
    unalias chruby 2> /dev/null
    unalias ruby 2> /dev/null
    unalias bundle 2> /dev/null
    unalias gem 2> /dev/null

    # Loads Homebrew.
    load-brew

    # Loads rbenv.
    if command -v rbenv &> /dev/null ; then
        eval "$(rbenv init - zsh)"
    fi

    # Loads RVM.
    pathadd PATH ${HOME}/.rvm/bin > /dev/null
    if [ -f $HOME/.rvm/scripts/rvm ]; then
        source $HOME/.rvm/scripts/rvm
    fi

    # Loads chruby.
    local found_chruby=0
    if [ -f /opt/homebrew/opt/chruby/share/chruby/chruby.sh ]; then
        source /opt/homebrew/opt/chruby/share/chruby/chruby.sh
        source /opt/homebrew/opt/chruby/share/chruby/auto.sh
        found_chruby=1
    elif [ -f /usr/local/share/chruby/chruby.sh ]; then
        source /usr/local/share/chruby/chruby.sh
        source /usr/local/share/chruby/auto.sh
        found_chruby=1
    fi

    # Gets the latest version in ~/.rubies
    if [ $found_chruby -eq 1 ]; then
        local latest_ruby=$(\ls -1 ${HOME}/.rubies | tail -1)
        if [ -n "$latest_ruby" ]; then
            chruby $latest_ruby
        else
            echo "No rubies found in ${HOME}/.rubies"
        fi
    fi
}

alias rbenv='load-ruby && \rbenv'
alias rvm='load-ruby && \rvm'
alias chruby='load-ruby && \chruby'
alias ruby='load-ruby && \ruby'
alias bundle='load-ruby && \bundle'
alias gem='load-ruby && \gem'

# Homebrew
export HOMEBREW_PREFIX=/opt/homebrew
load-brew() {
    unalias brew 2> /dev/null

    if [ -d $HOMEBREW_PREFIX ]; then
        pathadd PATH ${HOMEBREW_PREFIX}/bin > /dev/null
        eval "$(/opt/homebrew/bin/brew shellenv)"

        pathadd C_INCLUDE_PATH ${HOMEBREW_PREFIX}/include/ > /dev/null
        pathadd CPLUS_INCLUDE_PATH ${HOMEBREW_PREFIX}/include/ > /dev/null
        pathadd LIBRARY_PATH ${HOMEBREW_PREFIX}/lib > /dev/null
    fi
}

alias brew='load-brew && \brew'

# Conda
export CONDA_DIR="${HOME}/.miniconda3"
export DEFAULT_PYTHON_VERSION=3.12

# History search
alias hgr='history | grep'

# React
export REACT_EDITOR=vscode

# Alert
alias alert='notify-send --urgency=low -i "$([ $? = 0  ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# -------------------
# Manage temp scripts
# -------------------

export TMP_SCRIPT_ROOT=$HOME/.tmp-scripts/

(mkdir -p $TMP_SCRIPT_ROOT $SLURM_LOG_DIR $LOG_DIR $EVAL_DIR $DATA_DIR $DATA_CACHE_DIR $MODEL_DIR $STAGE_DIR &)

_print_available_scripts() {
    find $TMP_SCRIPT_ROOT -type f | cut -c${#TMP_SCRIPT_ROOT}- | sed 's:/*::'
}

tdelete() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: tdelete <script>"
        return 1
    fi
    local filename=$1
    local filepath=$TMP_SCRIPT_ROOT/$filename
    if [[ ! -f "${filepath}" ]]; then
        echo "[ ${filename} ] doesn't exist! Available:"
        _print_available_scripts
    else
        rm "${filepath}"
        find $TMP_SCRIPT_ROOT -type d -empty -delete
    fi
}

tedit() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: tedit <script>"
        return 1
    fi
    local filename=$1
    local filepath=$TMP_SCRIPT_ROOT/$filename
    if [[ ! -f "${filepath}" ]]; then
        echo "[ ${filename} ] doesn't exist! Available:"
        _print_available_scripts
    else
        $EDITOR "${filepath}"
    fi
}

tinit() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: tinit <script>"
        return 1
    fi
    local filename=$1
    local filepath=$TMP_SCRIPT_ROOT/$filename
    mkdir -p $(dirname "$filepath")

    if [[ -f "${filepath}" ]]; then
        echo "[ ${filename} ] already exist! Existing files:"
        _print_available_scripts
    else
        touch ${filepath}
        chmod +x "${filepath}"
        tedit $filename
    fi
}

trun() {
    if [[ $# -lt 1 ]]; then
        echo "Usage: trun <script>"
        return 1
    fi
    local filename=$1
    shift
    local filepath=$TMP_SCRIPT_ROOT/$filename
    if [[ ! -f "${filepath}" ]]; then
        echo "[ ${filename} ] doesn't exist! Available:"
        _print_available_scripts
    else
        ${filepath} $@
    fi
}

# --------------------------------
# Download files from Google Drive
# --------------------------------

gdrive() {
    if [[ $# -ne 2 ]]; then
        echo "Usage: gdrive <google-fid> <output-path>"
        return 1
    fi
    local FILEID="$1"
    local FILENAME="$2"
    O=$(wget \
        --quiet \
        --save-cookies /tmp/gdrive-cookies.txt \
        --keep-session-cookies \
        --no-check-certificate \
        "https://docs.google.com/uc?export=download&id=${FILEID}" -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')
    wget \
        --load-cookies /tmp/gdrive-cookies.txt \
        "https://docs.google.com/uc?export=download&confirm=${O}&id=${FILEID}" -O $FILENAME
    rm -f /tmp/gdrive-cookies.txt
    return 0
}

# --------------------------------
# Edit conda environment variables
# --------------------------------

cn-vars() {
    if [[ ! -n $CONDA_PREFIX ]] || [[ "$CONDA_DEFAULT_ENV" == "base" ]]; then
        echo "Can't edit outside of Conda environment"
        return 1
    fi

    local CONDA_ENV_NAME=$(basename $CONDA_PREFIX)
    local ACTIVATE=$CONDA_PREFIX/etc/conda/activate.d/env_vars.sh
    local DEACTIVATE=$CONDA_PREFIX/etc/conda/deactivate.d/env_vars.sh
    mkdir -p $(dirname $ACTIVATE) $(dirname $DEACTIVATE)

    local WRITE_ACTIVATE=1
    local WRITE_DEACTIVATE=1
    [[ -f $ACTIVATE ]] && WRITE_ACTIVATE=false
    [[ -f $DEACTIVATE ]] && WRITE_DEACTIVATE=false

    local EDIT_ACTIVATE=0
    local EDIT_DEACTIVATE=0

    while [[ $# -gt 0 ]]; do
        case $1 in
        rm | r)
            rm $ACTIVATE $DEACTIVATE
            ;;
        rm-activate | ra)
            rm $ACTIVATE
            ;;
        rm-deactivate | rd)
            rm $DEACTIVATE
            ;;
        activate | a)
            EDIT_ACTIVATE=1
            ;;
        deactivate | d)
            EDIT_DEACTIVATE=1
            ;;
        *)
            echo "Invalid option: $1. Expected one of"
            echo "  - rm {r}"
            echo "  - rm-activate {ra}"
            echo "  - rm-deactivate {rd}"
            echo "  - activate {a}"
            echo "  - deactivate {d}"
            return 1
            ;;
        esac
        shift
    done

    if [[ $WRITE_ACTIVATE == 1 ]]; then
        echo "#!/bin/sh" >>$ACTIVATE
        echo "# $ACTIVATE" >>$ACTIVATE
        echo "" >>$ACTIVATE
    fi
    if [[ $WRITE_DEACTIVATE == 1 ]]; then
        echo "#!/bin/sh" >>$DEACTIVATE
        echo "# $DEACTIVATE" >>$DEACTIVATE
        echo "" >>$DEACTIVATE
    fi

    [[ $EDIT_ACTIVATE == 1 ]] && $EDITOR $ACTIVATE
    [[ $EDIT_DEACTIVATE == 1 ]] && $EDITOR $DEACTIVATE

    echo "Done editing environment variables for $CONDA_PREFIX; reloading..."
    conda deactivate
    conda activate $CONDA_ENV_NAME
    return 0
}

# ------------------------------
# Create a new Conda environment
# ------------------------------

cn-new() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: cn-new <env-name>"
        return 1
    fi
    local ENV_NAME=$1
    load-conda
    conda create -n $ENV_NAME python=$DEFAULT_PYTHON_VERSION
    conda deactivate
    conda activate $ENV_NAME
}

cn-env() {
    load-conda
    conda activate $@
}

cn-rm() {
    load-conda
    if [[ "$CONDA_DEFAULT_ENV" -eq "$1" ]]; then
        conda deactivate
    fi
    conda remove --all --name $@
}

# ---------------------------
# Activate a Pixi environment
# ---------------------------

px-env() {
    # Check for .pixi directory
    if [[ ! -d .pixi ]]; then
        warn-with-red-background "Pixi environment not found!"
        return 1
    fi
    load-pixi
    eval "$(\pixi shell-hook)"
}

# ---------------------------
# Create a new UV environment
# ---------------------------

uv-env() {
    local env_path=${HOME}/.virtualenvs/$1
    if [[ -d ${env_path} ]]; then
        source ${env_path}/bin/activate
    else
        # Create new environment if it doesn't exist
        load-uv
        mkdir -p ${HOME}/.virtualenvs
        if [[ $# -eq 1 ]]; then
            uv venv ${env_path} --python ${DEFAULT_PYTHON_VERSION}
        elif [[ $# -eq 2 ]]; then
            uv venv ${env_path} --python $2
        else
            echo "Usage: uv-env <env-name> (<python-version>)"
            return 1
        fi
        source ${env_path}/bin/activate
    fi
}

uv-rm() {
    if [[ "$#" -ne "1" ]]; then
        echo "Usage: uv-rm <name>"
        return
    fi
    rm -rf ${HOME}/.virtualenvs/$1
    echo "Removed environment '$1'"
}

# Use UV instead of regular PIP.
alias pip='uv pip'
alias pip3='uv pip'

# ---------------
# Tools for Slurm
# ---------------

# The user should override this in their local file.
export SLURM_GPUNODE_PARTITION=missing
export SLURM_GPUNODE_NUM_GPUS=1
export SLURM_GPUNODE_CPUS_PER_GPU=8
export SLURM_CPUNODE_PARTITION=missing
export SLURM_CPUNODE_NUM_CPUS=8
export SLURM_XPUNODE_SHELL=$SHELL

gpunode() {
    if [[ $# -ne 0 ]] && [[ $# -ne 1 ]]; then
        echo "Usage: gpunode (<num-gpus>)"
        return 1
    fi
    local num_gpus=${1:-$SLURM_GPUNODE_NUM_GPUS}

    # First, queries Slurm to see if there is an active job.
    # If so, attach to that job ID instead of creating a new job.
    # Query is based on the job name "gpunode".
    local job_id=$(squeue -u $USER -h -t R -o %i -n gpunode)
    if [[ -n $job_id ]]; then
        echo "Attaching to job ID $job_id"
        srun \
            --jobid=$job_id \
            --partition=$SLURM_GPUNODE_PARTITION \
            --gpus=$num_gpus \
            --cpus-per-gpu=$SLURM_GPUNODE_CPUS_PER_GPU \
            --pty $SLURM_XPUNODE_SHELL
        return 0
    fi

    echo "Creating new job"
    srun \
        --partition=$SLURM_GPUNODE_PARTITION \
        --gpus=$num_gpus \
        --cpus-per-gpu=$SLURM_GPUNODE_CPUS_PER_GPU \
        --interactive \
        --job-name=gpunode \
        --pty $SLURM_XPUNODE_SHELL
}

cpunode() {
    echo "Creating new job"
    srun \
        --partition=$SLURM_CPUNODE_PARTITION \
        --cpus-per-task=$SLURM_CPUNODE_NUM_CPUS \
        --interactive \
        --job-name=cpunode \
        --pty $SLURM_XPUNODE_SHELL
}

# ----------------
# Tools for `make`
# ----------------

brun() {
    if [ $# -lt 1 ]; then
        echo "Usage: brun <fpath> (runtime-args)"
        echo "  Make a file (if not up-to-date), then run it if make succeeds"
        return 1
    fi

    local fpath=$1
    shift

    local fname=$(basename "$fpath")
    local dname=$(dirname "$fpath")
    cd $dname

    local extname=$(find $dname -type f -name "$fname.*" | head -1)
    if [[ -n ${extname} ]]; then
        echo "Assuming you meant '${extname}'"
        fname=$extname
    fi

    local base="${fname%.*}"
    local ext=$(echo "${fname##*.}" | awk '{print tolower($0)}')

    case $ext in
        $base)
            echo "No extension found"
            ;;
        cc|cpp|c)
            make $base && ./$base $@
            ;;
        cu)
            nvcc $base.$ext -o $base && ./$base $@
            ;;
        *)
            echo "Extension not supported: $ext"
            ;;
    esac

    cd -
}

# ---------------------
# Query GPU Utilization
# ---------------------

smiq() {
    local options outf query_str

    options=(
        timestamp
        name
        driver_version
        pstate
        pcie.link.gen.max
        pcie.link.gen.current
        temperature.gpu
        utilization.gpu
        utilization.memory
        memory.total
        memory.free
        memory.used
    )

    outf=/tmp/gpu-usage-$HOSTNAME.csv
    echo "Writing to $outf"

    query_str=$(printf ",%s" "${options[@]}")
    query_str=${query_str:1}

    nvidia-smi \
        --query-gpu=$query_str \
        --format=csv \
        --loop-ms=500 \
        --filename=$outf \

    return 0
}

# --------------------
# Writes storage usage
# --------------------

get-storage() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: get-storage <fpath>"
        return 1
    fi

    fpath=$1
    shift

    # Creates a temporary file for reading errors.
    local tmpfile=$(mktemp /tmp/abc-script.XXXXXX)

    # Removes existing file path.
    rm -f $fpath

    # Logs current date.
    date 2>> $tmpfile >> $fpath
    echo "" >> $fpath

    # Logs information about the entire file system.
    df -h -a 2>> $tmpfile >> $fpath

    # Logs information about the local disk.
    echo "" >> $fpath
    echo "===== LOCAL DISK =====" >> $fpath
    df -h ${HOME} 2>> $tmpfile >> $fpath

    # Logs the top offending directories.
    echo "" >> $fpath
    echo "===== TOP DIRECTORIES =====" >> $fpath
    du -h -d 4 2>> $tmpfile | sort -r -h >> $fpath

    # Appends error messages, if there are any.
    if [[ -s $tmpfile ]]; then
        echo "" >> $fpath
        echo "===== ERRORS =====" >> $fpath
        cat $tmpfile >> $fpath
    fi
    rm $tmpfile

    chmod 444 $fpath
}

# ------------------
# Less on file group
# ------------------

gless() {
    if [[ $# -lt 1 ]]; then
        echo "Usage: gless <file-group>"
        return 1
    fi
    sed -s '$a\\n[ ---------- ]\n' $@ | less
}

alias eless='2>&1 | less'

# ---------------
# Docker commands
# ---------------

alias docker-kill='docker ps -aq | xargs docker stop | xargs docker rm'
alias docker-clean='docker-kill && docker image prune -a -f && docker volume prune -f'

# ---------------------------------
# Manage path environment variables
# ---------------------------------

pathadd() {
    if [[ $# -ne 2 ]] && [[ $# -ne 3 ]]; then
        echo "Usage: pathadd <var> <new-path>"
        return 1
    fi
    local var=$1
    local new_path=$2
    local prev_val="$(env-val $var):"
    if [[ -d "${new_path}" ]]; then
        if [[ ":${prev_val}:" != *":${new_path}:"* ]]; then
            if [[ $# -eq 3 ]] && [[ $3 == "append" ]]; then
                export ${var}=${prev_val}:${new_path}
            else
                export ${var}=${new_path}:${prev_val}
            fi
        fi
    else
        echo "Missing: ${new_path}"
    fi
}

pathclean() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: pathclean <var>"
        return 1
    fi
    local var=$1
    local prev_val="$(env-val $var):"
    local new_val
    echo ${prev_val} | while read -d ':' dir; do
        if [[ ":${new_val}:" != *":${dir}:"* ]] && [[ -d ${dir} ]]; then
            new_val="${new_val:+"$new_val:"}${dir}"
        fi
        export ${var}="${new_val}"
    done
}

killport() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: killport <port>"
        return 1
    fi
    local port=$1
    local pids=$(lsof -i :${port} | grep LISTEN | awk '{print $2}' | sort -u | tr '\n' ' ')
    if [[ -n ${pid} ]]; then
        echo "Killing process(es) '${pids}' on port ${port}"
        echo ${pids} | xargs kill -9
    fi
}

killproc() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: killproc <name>"
        return 1
    fi
    local name=$1
    local pids=$(pgrep -f ${name})
    if [[ -n ${pids} ]]; then
        local pids_str=$(echo ${pids} | tr '\n' ' ')
        echo "Killing '${name}' processes ${pids_str}"
        echo ${pids} | xargs kill -9
    fi
}

killgpu() {
    if [[ ! -x $(command -v nvidia-smi) ]]; then
        return 0
    fi
    local gpu_procs=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | awk '{print $1}')
    if [[ -n ${gpu_procs} ]]; then
        local gpu_procs_str=$(echo ${gpu_procs} | tr '\n' ' ')
        echo "Killing GPU processes ${gpu_procs_str}"
        echo ${gpu_procs} | xargs kill -9
    fi
}

killml() {
    killport 9249
    killport 29500
    killproc tensorboard
    killproc runml
    killproc mlfab
    killgpu
}

shell-str() {
    echo $SHELL | awk -F/ '{print $NF}'
}

load-conda() {
    unalias conda 2> /dev/null

    conda_sh=${CONDA_DIR}/etc/profile.d/conda.sh
    if [ -f "${conda_sh}" ]; then
        . "${conda_sh}"
    else
        pathadd PATH $CONDA_DIR/bin/
    fi

    # If Conda is unavailable, show a warning and return.
    if [[ ! -d ${CONDA_DIR} ]]; then
        warn-with-red-background "Conda not installed to \$CONDA_DIR"
        return 0
    fi

    local conda_setup=$("${CONDA_DIR}/bin/conda" "shell.$(shell-str)" 'hook')
    eval $conda_setup
}

alias conda='load-conda && \conda'

load-cargo() {
    unalias cargo 2> /dev/null
    pathadd PATH ${HOME}/.cargo/bin/
}

alias cargo='load-cargo && \cargo'

load-uv() {
    unalias uv 2> /dev/null
    if [[ -d ${HOME}/.cargo/bin/ ]]; then
        pathadd PATH ${HOME}/.cargo/bin/
    fi
    if ! command -v uv &> /dev/null; then
        echo "Installing UV"
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    if [[ -d ${HOME}/.cargo/bin/ ]]; then
        pathadd PATH ${HOME}/.cargo/bin/
    fi
}

alias uv='load-uv && \uv'

load-pixi() {
    unalias pixi 2> /dev/null
    if [[ -d ${HOME}/.cargo/bin ]]; then
        pathadd PATH ${HOME}/.cargo/bin
    fi
    local pixi_dir=${HOME}/.pixi/bin
    if [[ ! -d ${pixi_dir} ]]; then
        echo "Installing pixi"
        curl -fsSL https://pixi.sh/install.sh | bash
    fi
    pathadd PATH ${pixi_dir}
    eval "$(pixi completion --shell $(shell-str))"
}

alias pixi='load-pixi && \pixi'

relink-directories() {
    if [[ $# -ne 2 ]]; then
        echo "Usage: relink-directories <dataset-dir> <checkpoints-dir>"
        return 1
    fi

    local dataset_dir=$1
    if [[ ! -d ${dataset_dir} ]]; then
        echo "Directory ${dataset_dir} does not exist"
        return 1
    fi
    dataset_dir=$(realpath $dataset_dir)

    local checkpoints_dir=$2
    if [[ ! -d ${checkpoints_dir} ]]; then
        echo "Directory ${checkpoints_dir} does not exist"
        return 1
    fi
    checkpoints_dir=$(realpath $checkpoints_dir)

    mkdir -p \
        ${dataset_dir}/data \
        ${dataset_dir}/cache

    mkdir -p \
        ${checkpoints_dir}/slurm \
        ${checkpoints_dir}/logs \
        ${checkpoints_dir}/evaluation \
        ${checkpoints_dir}/models \
        ${checkpoints_dir}/staging

    if [[ ! -d ${DATA_DIR} ]] || [[ ! -L ${DATA_DIR} ]]; then
        echo "Linking ${DATA_DIR} to ${dataset_dir}/cache"
        [[ -d ${DATA_DIR} ]] && rm -r ${DATA_DIR}
        ln -s ${dataset_dir}/data ${DATA_DIR}
    fi

    if [[ ! -d ${DATA_CACHE_DIR} ]] || [[ ! -L ${DATA_CACHE_DIR} ]]; then
        echo "Linking ${DATA_CACHE_DIR} to ${dataset_dir}/cache"
        [[ -d ${DATA_CACHE_DIR} ]] && rm -r ${DATA_CACHE_DIR}
        ln -s ${dataset_dir}/cache ${DATA_CACHE_DIR}
    fi

    if [[ ! -d ${SLURM_LOG_DIR} ]] || [[ ! -L ${SLURM_LOG_DIR} ]]; then
        echo "Linking ${SLURM_LOG_DIR} to ${checkpoints_dir}/slurm"
        [[ -d ${SLURM_LOG_DIR} ]] && rm -r ${SLURM_LOG_DIR}
        ln -s ${checkpoints_dir}/slurm ${SLURM_LOG_DIR}
    fi

    if [[ ! -d ${LOG_DIR} ]] || [[ ! -L ${LOG_DIR} ]]; then
        echo "Linking ${LOG_DIR} to ${checkpoints_dir}/logs"
        [[ -d ${LOG_DIR} ]] && rm -r ${LOG_DIR}
        ln -s ${checkpoints_dir}/logs ${LOG_DIR}
    fi

    if [[ ! -d ${EVAL_DIR} ]] || [[ ! -L ${EVAL_DIR} ]]; then
        echo "Linking ${EVAL_DIR} to ${checkpoints_dir}/evaluation"
        [[ -d ${EVAL_DIR} ]] && rm -r ${EVAL_DIR}
        ln -s ${checkpoints_dir}/evaluation ${EVAL_DIR}
    fi

    if [[ ! -d ${MODEL_DIR} ]] || [[ ! -L ${MODEL_DIR} ]]; then
        echo "Linking ${MODEL_DIR} to ${checkpoints_dir}/models"
        [[ -d ${MODEL_DIR} ]] && rm -r ${MODEL_DIR}
        ln -s ${checkpoints_dir}/models ${MODEL_DIR}
    fi

    if [[ ! -d ${STAGE_DIR} ]] || [[ ! -L ${STAGE_DIR} ]]; then
        echo "Linking ${STAGE_DIR} to ${checkpoints_dir}/staging"
        [[ -d ${STAGE_DIR} ]] && rm -r ${STAGE_DIR}
        ln -s ${checkpoints_dir}/staging ${STAGE_DIR}
    fi

    return 0
}

waitport() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: waitport <port>"
        return 1
    fi
    local port=$1
    while [[ ! -z $(lsof -i :${port}) ]]; do
        sleep 1
    done
}

# ------------------------ #
# Machine Learning aliases #
# ------------------------ #

export HF_HOME=${MODEL_DIR}/huggingface

# ----------- #
# Git aliases #
# ----------- #

remove-git-submodule() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: remove-git-submodule <submodule-path>"
        return 1
    fi
    local submodule_path=$1

    # Checks that the path is a submodule.
    if [[ ! -f .gitmodules ]]; then
        echo "No .gitmodules file found"
        return 1
    fi
    if [[ -z $(grep -E "\[submodule \"${submodule_path}\"\]" .gitmodules) ]]; then
        echo "No submodule found at path ${submodule_path}"
        return 1
    fi

    git submodule deinit -f -- $submodule_path
    rm -rf $submodule_path
    git rm -f $submodule_path
    git config -f .gitmodules --remove-section submodule.$submodule_path
    git add .gitmodules
}

# -------------------
# Python installation
# -------------------

install-python-version() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: install-python-version <version>"
        return 1
    fi
    local version=$1
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt update -y
    sudo apt upgrade -y
    sudo apt install python${version} python${version}-venv python${version}-dev -y
}

install-python3.12() {
    install-python-version 3.12
}

install-python3.11() {
    install-python-version 3.11
}

install-python3.10() {
    install-python-version 3.10
}

install-python3.9() {
    install-python-version 3.9
}

install-python3.8() {
    install-python-version 3.8
}
