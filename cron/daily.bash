#!/bin/bash

# Sources bashrc to make sure Python is set correctly.
if [ -f ${HOME}/.bashrc ]; then
    . ${HOME}/.bashrc
fi

# Updates old dates.
${HOME}/.cron/manage_date_folders.bash

# Removes old slurm log directories.
if [ -d "$SLURM_LOG_DIR" ]; then
    find $SLURM_LOG_DIR -type d -mtime +7 | xargs -I {} -P 8 rm -r {} 2> /tmp/slurm_cleanup_$(date +'%Y-%m-%d').log
else
    echo "Missing slurm log directory: '$SLURM_LOG_DIR'"
fi

# Removes old run directories.
if [ -d "$RUN_DIR" ]; then
    find $RUN_DIR -type d -mtime +7 | xargs -I {} -P 8 rm -r {} 2> /tmp/run_cleanup_$(date +'%Y-%m-%d').log
else
    echo "Missing run directory: '$RUN_DIR'"
fi

# Removes empty log directories.
if [ -d "$LOG_DIR" ]; then
    find $LOG_DIR -maxdepth 2 -empty -type d -mtime +2 | xargs -I {} -P 8 rm -r {} 2> /tmp/log_cleanup_$(date +'%Y-%m-%d').log
    find $LOG_DIR -maxdepth 2 -name local.* -type d -mtime +1 | xargs -I {} -P 8 rm -r {} 2> /tmp/local_cleanup_$(date +'%Y-%m-%d').log
else
    echo "Missing log directory: '$LOG_DIR'"
fi

# Removes empty eval directories.
if [ -d "$EVAL_DIR" ]; then
    find $EVAL_DIR -maxdepth 2 -empty -type d -mtime +2 | xargs -I {} -P 8 rm -r {} 2> /tmp/eval_cleanup_$(date +'%Y-%m-%d').log
else
    echo "Missing eval directory: '$EVAL_DIR'"
fi

# Runs local cron script, if found.
if [ -f ${HOME}/.cron-local/daily.bash ]; then
    . ${HOME}/.cron-local/daily.bash
fi

# Computes storage space.
du -h -d 4 | sort -h > ${HOME}/storage
