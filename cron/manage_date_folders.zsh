#!/bin/zsh

# ddate (Delta Date) is defined in shell/aliases.sh.
source ~/.shell/aliases.sh
source ~/.zsh/aliases.zsh

load-brew

start_date=$(ddate 360 +'%Y-%m-%d')
end_date=$(ddate 180 +'%Y-%m-%d')
yesterday=$(ddate 1 +'%Y-%m-%d')
today=$(date +"%Y-%m-%d")

# Deletes any date folders older than 180 days.
__delete_old_dates() {
    root=$1

    python3 ~/.scripts/manage_dates \
        $root \
        -s $start_date \
        -e $end_date \
        -a delete 2> /dev/null
}

# Updates the daily symlink to point to today.
__update_symlinks() {
    root=$1
    root_today=$root/$today
    root_yesterday=$root/$yesterday
    mkdir -p $root_today

    # Updates directory for today.
    if [ -L $root/today ]; then
        unlink $root/today
    fi
    ln -s $root_today $root/today
    chmod -R 755 $root_today

    # Updates directory for yesterday.
    if [ -L $root/yesterday ]; then
        unlink $root/yesterday
    fi
    ln -s $root_yesterday $root/yesterday

    return 0
}

manage_date_folders() {
    if [ $# -ne 1 ]; then
        echo "Usage: update_symlinks <root>"
    fi
    root=$1
    shift
    mkdir -p $root

    __update_symlinks $root
    __delete_old_dates $root
}

[ -n $LOG_DIR ] && [ -d $LOG_DIR ] && manage_date_folders $LOG_DIR
[ -n $EVAL_DIR ] && [ -d $EVAL_DIR ] && manage_date_folders $EVAL_DIR
