#!/bin/bash
./proxyd.py &
sleep 2
#python proxy/mipclient.py
python proxy/mipclient.py &
#sleep 1
#ssh -p 8115 localhost
