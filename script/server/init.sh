#!/bin/bash -x

basedir=`dirname $0`

cd $basedir

for dir in `ls`
do
	if [ -d $dir ]
	then
		pushd $dir
		bash -x init.sh
		popd
	fi
done
