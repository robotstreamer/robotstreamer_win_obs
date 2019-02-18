import pyautogui
import time
freePongActive = False
#todo: should be called process command
def handleCommand(command, keyPosition):
                if command[0:5] == 'KEY_':
                                code = command[5:].lower()
                                print("pressing:", code)
                                pyautogui.press(code)

