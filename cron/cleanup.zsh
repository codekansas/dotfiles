#!/bin/zsh

# Gets project-specific aliases.
source ~/.shell/aliases.sh

cleanup_logfile=/tmp/${USER}_cleanup_$(date +'%Y-%m-%d').log

# Removes empty log directories.
if [ -d "$LOG_DIR" ]; then
    find "$LOG_DIR/" \
        -mindepth 1 \
        -maxdepth 2 \
        -empty \
        -type d \
        -mtime +2 | xargs -I {} -P 8 rm -r {} 2>> $cleanup_logfile
else
    echo "Missing log directory: '$LOG_DIR'"
fi

# Removes empty eval directories.
if [ -d "$EVAL_DIR" ]; then
    find "$EVAL_DIR/" \
        -mindepth 1 \
        -maxdepth 2 \
        -empty \
        -type d \
        -mtime +2 | xargs -I {} -P 8 rm -r {} 2>> $cleanup_logfile
else
    echo "Missing eval directory: '$EVAL_DIR'"
fi

# If no logs were written, remove the logfile.
if [ -s $cleanup_logfile ]; then
    echo "Found errors while running cleanup script; written to ${cleanup_logfile}"
else
    rm $cleanup_logfile
fi
