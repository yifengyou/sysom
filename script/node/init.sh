#!/bin/bash -x

basedir=`dirname $0`

cd $basedir

for i in `cat conf`
do
    export $i
done

cp -f conf ${APP_HOME}/

for dir in `ls`
do
    if [ -d $dir ]
    then
        pushd $dir
        bash -x init.sh
        popd
    fi
done
