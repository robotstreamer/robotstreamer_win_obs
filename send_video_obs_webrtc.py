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
#import audio_util
import urllib.request
import rtc_signaling

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
streamKey = commandArgs.stream_key

lastCharCount = None
robotSettings = None
resolutionChanged = False
currentXres = None
currentYres = None
audioProcess = None
videoProcess = None


def getVideoSFU():
    url = '%s/v1/get_endpoint/webrtc_sfu/100' % (apiServer)
    response = robot_util.getWithRetry(url)
    return json.loads(response)


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



def startVideoRtc(videoEndpoint, SSRC):

    videoHost = videoEndpoint['localIp']
    videoPort = videoEndpoint['localPort']
    print("startVideoRtc endpoints:", videoHost, videoPort)

    videoCommandLine = 'ffmpeg -r 30 -f dshow -i video="OBS-Camera" -video_size {xres}x{yres} \
                        -map 0:v:0 -pix_fmt yuv420p -c:v libx264 -b:v {kbps}k -preset ultrafast -g 50 -f tee \
                        \"[select=v:f=rtp:ssrc={SSRC}:payload_type=101]rtp://{video_host}:{video_port}\"'\
                        .format(kbps=robotSettings.kbps, 
                                video_host=videoHost, 
                                video_port=videoPort, 
                                SSRC=SSRC, 
                                xres=robotSettings.xres, 
                                yres=robotSettings.yres)
    
    print(videoCommandLine)
    return subprocess.Popen(shlex.split(videoCommandLine))



def startAudioRtc(audioEndpoint, SSRC):

    audioHost = audioEndpoint['localIp']
    audioPort = audioEndpoint['localPort']
    print("startAudioRtc endpoints:", audioHost, audioPort)

    audioCommandLine = 'ffmpeg -f dshow -i audio="OBS-Audio" -map 0:a:0 -acodec libopus -ab 128k -ac 2 -ar 48000 -f tee \"[select=a:f=rtp:ssrc=%s:payload_type=100]rtp://%s:%s\"'\
                        % ( #robotSettings.audio_rate, #locked for now
                            #robotSettings.mic_channels, 
                            str(SSRC),
                            audioHost, 
                            audioPort, 
                        )

    print(audioCommandLine)
    return subprocess.Popen(shlex.split(audioCommandLine))


def startDualTest(videoEndpoint, SSRCV, audioEndpoint, SSRCA):

    audioHost = audioEndpoint['localIp']
    audioPort = audioEndpoint['localPort']
    videoHost = videoEndpoint['localIp']
    videoPort = videoEndpoint['localPort']
    print("startDualTest endpoints:", videoHost, videoPort, audioHost, audioPort)

    videoCommandLine = 'ffmpeg\
                        -r 30 -f dshow -i video="OBS-Camera" \
                        -f dshow -i audio="OBS-Audio" \
                        -pix_fmt yuv420p -c:v libx264 -b:v {kbps}k -maxrate {kbps}k -minrate {kbps}k -bufsize 100k -g 50 -preset ultrafast -map 0:v:0 \
                        -c:a libopus -b:a 128k -ac 2 -ar 48000 -map 1:a:0\
                        -f tee "[select=a:f=rtp:ssrc={SSRCA}:payload_type=100]rtp://{audio_host}:{audio_port}|[select=v:f=rtp:ssrc={SSRCV}:payload_type=101]rtp://{video_host}:{video_port}"'\
                        .format(kbps=robotSettings.kbps, 
                                audio_host=audioHost, 
                                audio_port=audioPort, 
                                video_host=videoHost, 
                                video_port=videoPort, 
                                SSRCA=SSRCA, 
                                SSRCV=SSRCV, 
                                xres=robotSettings.xres, 
                                yres=robotSettings.yres)
    print(videoCommandLine)
    return subprocess.Popen(shlex.split(videoCommandLine))



def main():

    global robotID
    global audioProcess
    global videoProcess
    refreshFromOnlineSettings()

    # overrides command line parameters using config file
    print("args on command line:", commandArgs)
    print("camera id:", commandArgs.camera_id)
    print("args after loading from server:", robotSettings)
    print (streamKey)

    videoSSRC = int(random.randint(10000,99999))
    audioSSRC = int(random.randint(10000,99999))
    peerID    = str(random.randint(100000,999999)) #need to ditch peer ids anyway

    print("videoSSRC: ", videoSSRC)
    print("audioSSRC: ", audioSSRC)


    videoSFU = getVideoSFU()
    print("webrtc SFU: ", videoSFU)

    robotID = str(int(commandArgs.camera_id) - int(100)) #just for temp compatability
    print("robotID: ", robotID)

    ws = rtc_signaling.SFUClient('wss://'+str(videoSFU['host'])+':'+str(videoSFU['port'])\
                                  +'/?roomId='+robotID+'&peerId=p:robot_'+peerID, protocols=['protoo'])
    ws.init(streamKey, videoSSRC, audioSSRC)
    ws.connect()
    ws.getRouterRtpCapabilities()   #not required
    ws.requestPlainTransportVideo() #build transports then producers 
    ws.requestPlainTransportAudio() #build transports then producers

    #janky blocking. this is just a test afterall
    while ws.videoEndpoint == False:
        pass
    
    while ws.audioEndpoint == False:
        pass

   # startVideoRtc(ws.videoEndpoint, videoSSRC)
   # startAudioRtc(ws.audioEndpoint, audioSSRC)
    startDualTest(ws.videoEndpoint, videoSSRC, ws.audioEndpoint, audioSSRC)

    sys.stdout.flush()
    ws.run_forever()



main()
