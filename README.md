install python-3.6.6-amd64.exe or similar
run install_deps.bat #it does (pip install websockets)

install obs-virtualcam (OBS-VirtualCam1.2.1.zip)
	1.Unzip OBS-VirtualCam1.2.1.zip and put it to your obs-studio install folder
	2.Run CMD as Administrator and register 32bit directshow source
	ex: regsvr32 "C:\Program Files (x86)\obs-studio\bin\32bit\obs-virtualsource.dll"
	3.Do it again to register 64bit directshow source
	ex: regsvr32 "C:\Program Files (x86)\obs-studio\bin\64bit\obs-virtualsource.dll"

open OBS and go to Tools > Virtualcam
	enable autostart and click start if its not started already

if ffmpeg.exe and ffplay.exe are not in the folder get them here..
https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-20180630-9f0077c-win64-static.zip
unzip into this folder

same with espeak
http://sourceforge.net/projects/espeak/files/espeak/espeak-1.48/setup_espeak-1.48.04.exe
it extracts to C:\Program Files (x86)\eSpeak\command_line

copy the espeak.exe to this folder

edit start.bat with your details
