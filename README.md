RobotStreamer is a low latency live streaming platform. Stream from you desktop. Connect your movable cameras with TTS (robots) to RobotStreamer.com.

Broadcasters make the rules for their channels. Unlike most platforms, RobotStreamer is open to just about any content. Just maintain basic ethical decency, keep it legal, and keep it entertaining. For language, it's up to the broadcaster to decide how they want to moderate if at all.

You can create streams with Robots (movable cameras with TTS), that's our specialty, and you can also create tradional live IRL streams or game streams from the desktop. We currently use a different protocol than most live streaming platforms for lower latency.

We have a system called funbits that lets the streamers monetize their streams.

Note: This repo is for desktop streams. If you are making a robot, you need to use a different project, see: https://github.com/robotstreamer/robotstreamer

Note: If you are using OBS and you have a 64bit computer, make sure you have 64bit OBS.

Here's where our community hangs out. If you have any questions, this is the place to go:
https://discord.gg/n6B7ymy



<h2>Setting up Desktop Stream</h2>

Visit www.robotstreamer.com/new_stream.html to get stream key and id's

You'll need to specify the stream key as a command line argument for send_video.py and controller.py. It's like this:

--stream-key YOURKEY





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



