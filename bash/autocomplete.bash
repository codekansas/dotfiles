# conda
alias cenv='conda activate'
_conda_complete() {
    local cur opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    opts="$(ls -1 $CONDA_ENV_ROOT | paste -sd ' ')"
    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
    return 0
}
if [[ -d $CONDA_ENV_ROOT ]]; then
    complete -F _conda_complete 'cenv'
fi

# tmux
alias tmuxc='tmux -CC a -t'
_tmuxc_complete(){
    local cur opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    opts="$(tmux list-sessions -F '#S' | paste -sd ' ')"
    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
    return 0
}
complete -F _tmuxc_complete tmuxc