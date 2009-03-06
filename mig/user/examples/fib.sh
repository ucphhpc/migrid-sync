#!/bin/bash
#
# Simple recursive Fibonacci

function fib() {
	local arg=$1
	local res=0
	# echo "fib called with arg: $arg"
	if [ $arg -lt 2 ]; then
		#echo "hit bottom of recursion: $arg"
		return $arg
	else
		# echo "recursing with arg: $arg"
		fib $((arg-1))
		res=$?
		fib $((arg-2))
		res=$((res+$?))
		# echo "result: $res"
		return $res
	fi
}

if [ $# -ne 1 ]; then
	echo "Usage: fib.sh VALUE"
	exit 1
fi

fib $1
echo "fib $1 is $?"

exit 0
