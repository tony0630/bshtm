#!/bin/bash
#PY=/home/oppoops/anaconda2/bin/python2
#PY=~/anaconda2/bin/python2
PY=python
NOW=$($PY getDate.py)
TARGET=./data/$NOW

mkdir -p ./data

if [ ! -d "$TARGET" ]; then
    mkdir -p $TARGET
    $PY crawler.py $TARGET
    $PY crawler.py $TARGET
    rm *.jpg
fi
