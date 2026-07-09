#!/data/data/com.termux/files/usr/bin/bash

sleep 30

su -c "export PATH=\$PATH:/data/data/com.termux/files/usr/bin && export TERM=xterm-256color && cd /sdcard/Download && python obf-wuyx_rejoin.py" <<EOF
1

EOF
