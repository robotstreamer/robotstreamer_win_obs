import os
import asyncio
import websockets
import time
import argparse
import json
import robot_util
import _thread
import traceback
import tempfile
import uuid



allowedVoices = ['en-us', 'af', 'bs', 'da', 'de', 'el', 'eo', 'es', 'es-la', 'fi', 'fr', 'hr', 'hu', 'it', 'kn', 'ku', 'lv', 'nl', 'pl', 'pt', 'pt-pt', 'ro', 'sk', 'sr', 'sv', 'sw', 'ta', 'tr', 'zh', 'ru']
tempDir = tempfile.gettempdir()
messagesToTTS = []
numActiveEspeak = 0
maximumTTSTime = 5


print("temporary directory:", tempDir)


parser = argparse.ArgumentParser(description='start robot control program')
parser.add_argument('robot_id', help='Robot ID')
parser.add_argument('--forward', default='[-1,1,-1,1]')
parser.add_argument('--left', default='[1,1,1,1]')
parser.add_argument('--no-secure-cert', dest='secure_cert', action='store_false')
parser.add_argument('--voice-number', type=int, default=1)
parser.add_argument('--male', dest='male', action='store_true')
parser.add_argument('--festival-tts', dest='festival_tts', action='store_true')
parser.add_argument('--enable-ping-pong', dest='enable_ping_pong', action='store_true')
parser.set_defaults(enable_ping_pong=False)
parser.add_argument('--tts-volume', type=int, default=80)
parser.add_argument('--tts-speed', type=int, default=200)
parser.add_argument('--type', default="rsbot")
parser.add_argument('--stream-key', default="123")
parser.add_argument('--straight-speed', type=int, default=255)
parser.add_argument('--turn-speed', type=int, default=255)
parser.add_argument('--api-url', default="http://api.robotstreamer.com:8080")
parser.add_argument('--play-with-ffplay', dest='play_with_ffplay', action='store_true')
parser.set_defaults(play_with_ffplay=False)

commandArgs = parser.parse_args()
print(commandArgs)
apiHost = commandArgs.api_url

if commandArgs.type == "rsbot":
            print("initializing rsbot")
            import rsbot_interface as interface
            interface.init(commandArgs,
                           json.loads(commandArgs.forward),
                           json.loads(commandArgs.left),
                           commandArgs.enable_ping_pong)

elif commandArgs.type == "windows_interface":
            import windows_interface as interface

elif commandArgs.type == "mac":
            import mac_interface as interface
            
elif commandArgs.type == "gopigo3":
            import gopigo3_interface as interface

elif commandArgs.type == "gopigo":
            import gopigo_interface as interface

elif commandArgs.type == "gopigomessedup":
            import gopigomessedup_interface as interface            

elif commandArgs.type == "roomba":
            import roomba_interface as interface
            interface.init()

elif commandArgs.type == "obs":
            import obs_interface as interface

            



def setVolume(percent):


    if commandArgs.type == "obs":
        pass #volume set in fplay
    else:
        print("setting volume to", percent, "%")
        for cardNumber in range(0, 5):
            for numid in range(0,5):
                os.system("amixer -c %d cset numid=%d %d%%" % (cardNumber, numid, percent))


def espeakWinOBS(hardwareNumber, message, voice):

            global numActiveEspeak
            
            numActiveEspeak += 1
            print("number of espeaks active", numActiveEspeak)

            try:
            
                        tempFilePath = os.path.join(tempDir, "text_" + str(uuid.uuid4()))
                        wavFile = os.path.join(tempDir, str(uuid.uuid4()) + ".wav")
                        croppedWavFile = os.path.join(tempDir, str(uuid.uuid4()) + ".wav")
                        f = open(tempFilePath, "w")
                        f.write(message)
                        f.close()

                        ttsSpeed  = commandArgs.tts_speed
                        ttsVolume = commandArgs.tts_volume

                        if commandArgs.male :
                            ttsPitch = 50    #roughly male   
                        else :
                            ttsPitch = 270   #roughly female 

                        messageFile = tempFilePath+"message.txt"
                        ftxt = open(messageFile, 'w')
                        ftxt.write(message)
                        ftxt.close()

                        if commandArgs.play_with_ffplay:
						
                            print("using espeak and ffplay")
                            cmd = 'espeak.exe -w %s -v%s+f%d -s%s -p%s -f %s' % (wavFile, voice, commandArgs.voice_number, ttsSpeed, ttsPitch, messageFile)
                            print(cmd)
                            os.system(cmd)


                            cropResult = os.system("ffmpeg -i %s -ss 0 -to %d -c copy %s" % (wavFile, maximumTTSTime, croppedWavFile))
                            print("crop result code", cropResult)
                            if cropResult == 0:
                                    print("play cropped")
                                    os.system('ffplay.exe %s -autoexit -nodisp -volume %s' % (croppedWavFile, ttsVolume))
                                    os.remove(croppedWavFile)
                            else:
                                    print("play full file")
                                    os.system('ffplay.exe %s -autoexit -nodisp -volume %s' % (wavFile, ttsVolume))                             
									
                            os.remove(wavFile)

                        else:
						
                            print("using just espeak")
                            cmd = 'espeak.exe -f %s' % messageFile
                            print(cmd)
                            os.system(cmd)
						
            
                        os.remove(tempFilePath)
                        os.remove(messageFile)


            except Exception as e:
                        print("something went wrong with espeak:", e)

            numActiveEspeak -= 1
            print("number of espeaks active", numActiveEspeak)




def say(message, voice='en-us'):

    os.system("killall espeak") #passes err in windows, too lazy to fix
    
    if voice not in allowedVoices:
        print("invalid voice")
        return
    
    tempFilePath = os.path.join(tempDir, "text_" + str(uuid.uuid4()))
    f = open(tempFilePath, "w")
    f.write(message)
    f.close()


    #os.system('"C:\Program Files\Jampal\ptts.vbs" -u ' + tempFilePath) Whaa?
    
    if commandArgs.festival_tts:
        # festival tts
        os.system('festival --tts < ' + tempFilePath)
    #os.system('espeak < /tmp/speech.txt')

    else:
        # espeak tts
        #todo: these could be defined in the interface modules perhaps

        if commandArgs.type == "mac":
                _thread.start_new_thread(espeakMac, (message, voice))

        if commandArgs.type == "obs":
            hardwareNumber = 0; 
            _thread.start_new_thread(espeakWinOBS, (hardwareNumber, message, voice))
        else:
            for hardwareNumber in (0, 2, 3, 1, 4):
                _thread.start_new_thread(espeak, (hardwareNumber, message, voice))


    os.remove(tempFilePath) #hmm




def getControlHost():

        url = apiHost+'/get_control_host_port/'+commandArgs.robot_id 

        response = robot_util.getWithRetry(url, secure=commandArgs.secure_cert)
        print("response:", response)
        return json.loads(response)
            
def getChatHost():

        #url = apiHost+'/v1/get_endpoint/rschat/'+commandArgs.robot_id #only for individual
        url = apiHost+'/v1/get_endpoint/rschat/100' 

        response = robot_util.getWithRetry(url, secure=commandArgs.secure_cert)
        print("response:", response)
        return json.loads(response)



async def handleControlMessages():


    controlGet = getControlHost()
    controlHost = controlGet['host']
    controlPort = controlGet['port']

    print("handle control messages get control port, connecting to port:", controlPort)
    url = 'ws://%s:%s/echo' % (controlHost, controlPort)

    async with websockets.connect(url) as websocket:

        print("connected to control service at", url)
        print("control websocket object:", websocket)

        # validation handshake
        await websocket.send(json.dumps({"command":commandArgs.stream_key}))
        
        while True:

            print("awaiting control message")
            
            message = await websocket.recv()
            print("< {}".format(message))
            j = json.loads(message)
            print(j)
            _thread.start_new_thread(interface.handleCommand, (j["command"],
                                                               j["key_position"]))

            
async def handleChatMessages():


    chatGet = getChatHost()
    chatHost = chatGet['host']
    chatPort = chatGet['port']

    url = 'ws://%s:%s' % (chatHost, chatPort)
    print("chat url:", url)

    async with websockets.connect(url) as websocket:

        print("connected to control service at", url)
        print("chat websocket object:", websocket)

        #todo: you do need this as an connection initializer, but you should make the server not need it
        await websocket.send(json.dumps({"message":"message"}))     

        while True:

            print("awaiting chat message")
            
            message = await websocket.recv()
            print("< {}".format(message))
            j = json.loads(message)
            print("message:", j)
            if ('message' in j) and ('tts' in j) and j['tts'] == True and (j['robot_id'] == commandArgs.robot_id):
                        messagesToTTS.append(j['message'])

            else:
                print("error, message not valid:", j)



            
def startControl():
    print("waiting a few seconds")
    time.sleep(6) #todo: only wait as needed (wait for interent)

    while True:
                print("starting control loop")
                time.sleep(0.25)
                try:
                            asyncio.new_event_loop().run_until_complete(handleControlMessages())
                except:
                            print("error")
                            traceback.print_exc()
                print("control event handler died")
                interface.movementSystemActive = False




def startChat():
        time.sleep(10) #todo: only wait as needed (wait for interenet)
        print("restarting loop")
        time.sleep(0.25)

        while True:
                    print("starting chat loop")
                    time.sleep(0.25)
                    
                    try:
                                asyncio.new_event_loop().run_until_complete(handleChatMessages())
                    except:
                                print("error")
                                traceback.print_exc()
                    print("chat event handler died")


def runPeriodicTasks():

            if len(messagesToTTS) > 0 and numActiveEspeak == 0:
                        message = messagesToTTS.pop(0)
                        _thread.start_new_thread(say, (message,))
  
  
def main():                

                     
            print(commandArgs)
            
            _thread.start_new_thread(startControl, ())
            _thread.start_new_thread(startChat, ())
            #_thread.start_new_thread(startTest, ())
            #startTest()

            setVolume(commandArgs.tts_volume)
            
            
            while True:
                time.sleep(0.20)
                runPeriodicTasks()


                
if __name__ == '__main__':
    main()


