#!/system/bin/sh

# Tunggu 30 detik setelah reboot
sleep 30

# Jalankan script Python
su -c '
export PATH=$PATH:/data/data/com.termux/files/usr/bin
export TERM=xterm-256color
cd /sdcard/Download
python obf-wuyx_rejoin.py &
'

# Koordinat tap (dibulatkan karena input tap menggunakan integer)
X1=1194
Y1=127

X2=251
Y2=451

X3=596
Y3=468

X4=1038
Y4=477

# Loop selamanya
while true
do
    su -c "input tap $X1 $Y1"
    sleep 60

    su -c "input tap $X2 $Y2"
    sleep 60

    su -c "input tap $X3 $Y3"
    sleep 60

    su -c "input tap $X4 $Y4"
    sleep 60
done
