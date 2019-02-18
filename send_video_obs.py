import subprocess
import shlex
import re
import os
import time
import platform
import json
import sys
import base64
import random
import datetime
import traceback
import robot_util
import _thread
import copy
import argparse
import urllib.request

from subprocess import Popen, PIPE
from threading import Thread
from queue import Queue


class DummyProcess:
    def poll(self):
        return None
    def __init__(self):
        self.pid = 123456789


parser = argparse.ArgumentParser(description='robot control')
parser.add_argument('camera_id')
parser.add_argument('window_title')
parser.add_argument('dummy_crap')

parser.add_argument('--api-server', help="Server that robot will connect to listen for API update events", default='http://api.robotstreamer.com:8080')
parser.add_argument('--xres', type=int, default=768)
parser.add_argument('--yres', type=int, default=432)
parser.add_argument('--audio-device-number', default=1, type=int)
parser.add_argument('--audio-device-name')
parser.add_argument('--kbps', default=350, type=int)
parser.add_argument('--brightness', type=int, help='camera brightness')
parser.add_argument('--contrast', type=int, help='camera contrast')
parser.add_argument('--saturation', type=int, help='camera saturation')
parser.add_argument('--rotate180', default=False, type=bool, help='rotate image 180 degrees')
parser.add_argument('--env', default="prod")
parser.add_argument('--screen-capture', dest='screen_capture', action='store_true') # tells windows to pull from different camera, this should just be replaced with a video input device option
parser.set_defaults(screen_capture=False)
parser.add_argument('--no-mic', dest='mic_enabled', action='store_false')
parser.set_defaults(mic_enabled=True)
parser.add_argument('--audio-rate', default=44100, type=int, help="this is 44100 or 48000 usually")
parser.add_argument('--no-restart-on-video-fail', dest='restart_on_video_fail', action='store_true')
parser.set_defaults(restart_on_video_fail=True)
parser.add_argument('--no-audio-restart', dest='audio_restart_enabled', action='store_false')
parser.set_defaults(audio_restart_enabled=True)
parser.add_argument('--no-camera', dest='camera_enabled', action='store_false')
parser.set_defaults(camera_enabled=True)
parser.add_argument('--dry-run', dest='dry_run', action='store_true')
parser.add_argument('--mic-channels', type=int, help='microphone channels, typically 1 or 2', default=1)
parser.add_argument('--audio-input-device', default='Microphone (HD Webcam C270)') # currently, this option is only used for windows screen capture
parser.add_argument('--stream-key', default='hellobluecat')
parser.add_argument('--ffmpeg-path', default='/usr/local/bin/ffmpeg')



commandArgs = parser.parse_args()
apiServer = commandArgs.api_server

lastCharCount = None
robotSettings = None
resolutionChanged = False
currentXres = None
currentYres = None
audioProcess = None
videoProcess = None


def getVideoEndpoint():
    url = '%s/v1/get_endpoint/jsmpeg_video_capture/%s' % (apiServer, commandArgs.camera_id)
    response = robot_util.getWithRetry(url)
    return json.loads(response)

def getAudioEndpoint():
    url = '%s/v1/get_endpoint/jsmpeg_audio_capture/%s' % (apiServer, commandArgs.camera_id)
    response = robot_util.getWithRetry(url)
    return json.loads(response)

def getOnlineRobotSettings(robotID):
    url = '%s/api/v1/robots/%s' % (apiServer, robotID)
    response = robot_util.getWithRetry(url)
    return json.loads(response)


def randomSleep():
    timeToWait = random.choice((0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 5))
    t = timeToWait * 3.0
    print("sleeping", t, "seconds")
    time.sleep(t)


def startVideoCaptureOBS():

    videoEndpoint = getVideoEndpoint()
    videoHost = videoEndpoint['host']
    videoPort = videoEndpoint['port']

    videoCommandLine = ("ffmpeg -r 30 -f dshow -i video='OBS-Camera' -video_size {xres}x{yres} -f mpegts -codec:v mpeg1video -s {xres}x{yres} -b:v {kbps}k -bf 0 -muxdelay 0.001 http://{video_host}:{video_port}/{stream_key}/{xres}/{yres}/"
    .format(kbps=robotSettings.kbps, 
            video_host=videoHost, 
            video_port=videoPort,
            xres=robotSettings.xres, 
            yres=robotSettings.yres, 
            stream_key=robotSettings.stream_key) )
    
    print(videoCommandLine)
    return subprocess.Popen(shlex.split(videoCommandLine))


def startAudioCaptureOBS():

    audioEndpoint = getAudioEndpoint()
    audioHost = audioEndpoint['host']
    audioPort = audioEndpoint['port']

    audioCommandLine = ("ffmpeg -f dshow -i audio='OBS-Audio' -ar %d -ac 2 -f mpegts -codec:a mp2 -b:a 128k -muxdelay 0.001 http://%s:%s/%s/640/480/"
    % ( robotSettings.audio_rate,
        audioHost, 
        audioPort,
        robotSettings.stream_key) )

    print(audioCommandLine)
    return subprocess.Popen(shlex.split(audioCommandLine))


def onCommandToRobot(*args):
    global robotID

    if len(args) > 0 and 'robot_id' in args[0] and args[0]['robot_id'] == robotID:
        commandMessage = args[0]
        print('command for this robot received:', commandMessage)
        command = commandMessage['command']

        if command == 'VIDOFF':
            print('disabling camera capture process')
            print("args", args)
            robotSettings.camera_enabled = False
            #todo: dress as cute girl and port this to windows
            #os.system("killall ffmpeg")

        if command == 'VIDON':
            if robotSettings.camera_enabled:
                print('enabling camera capture process')
                print("args", args)
                robotSettings.camera_enabled = True

        sys.stdout.flush()


def onConnection(*args):
    print('connection:', args)
    sys.stdout.flush()


def onRobotSettingsChanged(*args):
    print('---------------------------------------')
    print('set message recieved:', args)
    refreshFromOnlineSettings()


def killallFFMPEGIn30Seconds():
    time.sleep(30)
    #todo: dress as cute girl and port this to windows
    #os.system("killall ffmpeg")



#todo, this needs to work differently. likely the configuration will be json and pull in stuff from command line rather than the other way around.
def overrideSettings(commandArgs, onlineSettings):
    global resolutionChanged
    global currentXres
    global currentYres
    resolutionChanged = False
    c = copy.deepcopy(commandArgs)
    print("onlineSettings:", onlineSettings)
    if 'mic_enabled' in onlineSettings:
        c.mic_enabled = onlineSettings['mic_enabled']
    if 'xres' in onlineSettings:
        if currentXres != onlineSettings['xres']:
            resolutionChanged = True
        c.xres = onlineSettings['xres']
        currentXres = onlineSettings['xres']
    if 'yres' in onlineSettings:
        if currentYres != onlineSettings['yres']:
            resolutionChanged = True
        c.yres = onlineSettings['yres']
        currentYres = onlineSettings['yres']
    print("onlineSettings['mic_enabled']:", onlineSettings['mic_enabled'])
    return c


def refreshFromOnlineSettings():
    global robotSettings
    global resolutionChanged
    print("refreshing from online settings")
    #onlineSettings = getOnlineRobotSettings(robotID)
    #robotSettings = overrideSettings(commandArgs, onlineSettings)
    robotSettings = commandArgs

    if not robotSettings.mic_enabled:
        print("KILLING**********************")
        if audioProcess is not None:
            print("KILLING**********************")
            audioProcess.kill()

    if resolutionChanged:
        print("KILLING VIDEO DUE TO RESOLUTION CHANGE**********************")
        if videoProcess is not None:
            print("KILLING**********************")
            videoProcess.kill()

    else:
        print("NOT KILLING***********************")



def main():

    global robotID
    global audioProcess
    global videoProcess


    # overrides command line parameters using config file
    print("args on command line:", commandArgs)

    robot_util.sendCameraAliveMessage(apiServer, commandArgs.camera_id)

    refreshFromOnlineSettings()

    print("args after loading from server:", robotSettings)

    sys.stdout.flush()


    if robotSettings.camera_enabled:
        if not commandArgs.dry_run:
            videoProcess = startVideoCaptureOBS()
        else:
            videoProcess = DummyProcess()

    if robotSettings.mic_enabled:
        if not commandArgs.dry_run:
            audioProcess = startAudioCaptureOBS()
            _thread.start_new_thread(killallFFMPEGIn30Seconds, ())
        else:
            audioProcess = DummyProcess()


    numVideoRestarts = 0
    numAudioRestarts = 0

    count = 0


    # loop forever and monitor status of ffmpeg processes
    while True:

        time.sleep(1)

        if numVideoRestarts > 20:
            print("rebooting in 20 seconds because of too many restarts. probably lost connection to camera")
            time.sleep(20)

        if (count % robot_util.KeepAlivePeriod) == 0:
            robot_util.sendCameraAliveMessage(apiServer, commandArgs.camera_id)

        if robotSettings.camera_enabled:

            # restart video if needed
            if videoProcess.poll() != None:
                randomSleep()
                videoProcess = startVideoCaptureOBS()
                numVideoRestarts += 1
        else:
            print("video process poll: camera_enabled is false")



        if robotSettings.mic_enabled:

            if audioProcess is None:
                print("audio process poll: audioProcess object is None")
            else:
                print("audio process poll", audioProcess.poll(), "pid", audioProcess.pid, "restarts", numAudioRestarts)

            # restart audio if needed
            if (audioProcess is None) or (audioProcess.poll() != None):
                randomSleep()
                audioProcess = startAudioCaptureOBS()
                numAudioRestarts += 1


        count += 1


main()
