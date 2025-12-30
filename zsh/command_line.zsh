zcomet load ohmyzsh
zcomet load agkozak/zsh-z
zcomet load ohmyzsh plugins/gitfast
zcomet load ohmyzsh lib git.zsh

zcomet trigger zhooks agkozak/zhooks
zcomet trigger zsh-prompt-benchmark romkatv/zsh-prompt-benchmark

export ZSH_THEME_GIT_PROMPT_PREFIX=" on [%{$fg_bold[magenta]%}"
export ZSH_THEME_GIT_PROMPT_SUFFIX="%{$reset_color%}]"
export ZSH_THEME_GIT_PROMPT_DIRTY="%{$fg[red]%}!"
export ZSH_THEME_GIT_PROMPT_UNTRACKED="%{$fg[green]%}?"
export ZSH_THEME_GIT_PROMPT_CLEAN=""

export ZSH_THEME_RUBY_PROMPT_PREFIX="[%{$fg_bold[red]%}"
export ZSH_THEME_RUBY_PROMPT_SUFFIX="%{$reset_color%}]"

function conda_prompt_info {
    if [[ -n $CONDA_DEFAULT_ENV ]]; then
        case $CONDA_PREFIX in *"$CONDA_DEFAULT_ENV")
            echo " [%{$fg_bold[green]%}${CONDA_DEFAULT_ENV}%{$reset_color%}]"
        esac
    fi
}

function venv_prompt_info {
    if [[ -n $VIRTUAL_ENV ]]; then
        echo " [%{$fg_bold[yellow]%}$(basename $(dirname $VIRTUAL_ENV))%{$reset_color%}]"
    fi
}

function hostname_prompt_info {
    if [[ -n "$HOST" ]]; then
        echo " 🖥  [%{$fg[cyan]%}${HOST}%{$reset_color%}]"
    fi
}

function ruby_prompt_info_impl {
    local ruby_prompt_info_str=$(ruby_prompt_info)
    if [[ -n "$ruby_prompt_info_str" ]]; then
        echo " ${ruby_prompt_info_str}"
    fi
}

function tmux_prompt_info {
    if command -v tmux > /dev/null; then
        if [[ -n $TMUX ]]; then
            local msg=$(tmux display-message -p '#S' 2> /dev/null)
            if [[ -n $msg ]]; then
                echo " [%{$fg[magenta]%}${msg}%{$reset_color%}]"
            fi
        elif [[ ! -n $TMUX ]] && [[ $(tmux ls 2> /dev/null) ]]; then
            echo " [%{$fg[magenta]%}$(tmux ls | wc -l | tr -d ' ') sessions%{$reset_color%}]"
        fi
    fi
}

export PROMPT='[%{$fg[yellow]%}%~%{$reset_color%}]$(git_prompt_info)$(venv_prompt_info)$(conda_prompt_info)$(tmux_prompt_info)$(ruby_prompt_info_impl) ⌚ [%{$fg[red]%}%*%{$reset_color%}]$(hostname_prompt_info)
$ '

# We're already handling the virtual environment prompt.
export VIRTUAL_ENV_DISABLE_PROMPT=0

export CASE_SENSITIVE=true
export DISABLE_UPDATE_PROMPT=true
export ZSH_DISABLE_COMPFIX=true
export DISABLE_AUTO_TITLE=true
export UPDATE_ZSH_DAYS=14

zcomet load zsh-users/zsh-syntax-highlighting
zcomet load zsh-users/zsh-autosuggestions

zcomet compinit
