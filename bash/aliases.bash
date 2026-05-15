# -----------------------------------------------
# Prints value of an environment variable by name
# -----------------------------------------------

env-val() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: env-val <var>"
        return 1
    fi
    local var=$1
    echo ${!var}
}
