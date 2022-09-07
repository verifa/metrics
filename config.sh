#! /bin/sh

usage () {
    echo
    echo ${@}
cat <<EOF

 Usage:
    ${0} -path <folder for config> -repo <repo for config> -user <user w repo access> -passwd <password for repo user>

EOF
}

# There should be exactly 8 parameters
if [  "${#}" != "8" ]; then
    usage "Not enough parameters"
    exit 1
fi

mask=0

while [ -n "${1}" ]; do
  case ${1} in
    -path)
        mask=$(expr ${mask} + 1)
        shift
        CPATH=${1}
        ;;
    -repo)
        mask=$(expr ${mask} + 10)
        shift
        CREPO=${1}
        ;;
    -user)
        mask=$(expr ${mask} + 100)
        shift
        CUSER=${1}
        ;;
    -passwd)
        mask=$(expr ${mask} + 1000)
        shift
        CPASSWD=${1}
        ;;
    *)
        ;;
  esac
  shift
done

# Are there one each of the needed parameters
if [ "${mask}" != "1111" ]; then
    usage "There are missing parameters when calling ${0}"
    exit 2
fi

# Is there a config directory already, then wipe it out
if [ -d ${CPATH} ]; then
    rm -rf ${CPATH}/*
    rm -rf ${CPATH}/.git
fi

# Clone the config repo to the config path
git clone "https://${CUSER}:${CPASSWD}@${CREPO}" ${CPATH}
