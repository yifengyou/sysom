#!/bin/bash

check_cmd() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo >&2 "I require ${cmd} but it's not installed. Aborting."
        exit 1
    fi
}

green() {
    printf '\33[1;32m%b\n\33[0m' "$1"
}

check_cmd yarn
check_cmd tar

RELEASE=sysomRelease-$(date +"%Y%m%d%H%M%S")
APIDIR=sysom_api
WEBDIR=sysom_web
SCRIPTDIR=script
TOOLSDIR=tools
# build web
pushd sysom_web || exit
yarn
yarn build
popd || exit

mkdir -p "${RELEASE}"
cp -r ${APIDIR}/ ${TOOLSDIR}/ "${RELEASE}"/
cp -r ${WEBDIR}/dist/ "${RELEASE}"/${WEBDIR}/
mkdir -p "${RELEASE}"/${WEBDIR}/download/
cp ${TOOLSDIR}/deploy/deploy.sh "${RELEASE}"/
cp -r ${SCRIPTDIR} "${RELEASE}"/
tar czf "${RELEASE}".tar.gz "${RELEASE}"/
rm -rf "${RELEASE}"
green "The release pacakge is ${RELEASE}.tar.gz"
