# -*- coding: utf-8 -*-
"""

Pupil Labs Experiment : Mouse and Voice 

"""

"-----Mouse commands-----"
import mouse

# # left click
# mouse.click('left')

# # right click
# mouse.click('right')

# # middle click
# mouse.click('middle')

# # get mouse position
# mouse.get_position()

# # drag from (0, 0) to (100, 100) relatively with a duration of 0.1s
# mouse.drag(0, 0, 100, 100, absolute=False, duration=0.1)

# # whether the right button is clicked
# mouse.is_pressed("right")

# # move 100 right & 100 down
# mouse.move(100, 100, absolute=False, duration=0.2)

# # make a listener when left button is clicked
# mouse.on_click(lambda: print("Left Button clicked."))
# # make a listener when right button is clicked
# mouse.on_right_click(lambda: print("Right Button clicked."))

# # remove the listeners when you want
# mouse.unhook_all()

# # scroll down
# mouse.wheel(-1)

# # scroll up
# mouse.wheel(1)

# # record until you click right
# events = mouse.record()

# # replay these events
# mouse.play(events[:-1])

# Direct move of the mouse
# mouse.move(0,0,absolute=True,duration = 0)

"-----Voice commands-----"

import speech_recognition as sr
command=''

while command!='quit':
    r = sr.Recognizer()
    mic = sr.Microphone()
    sr.Microphone.list_microphone_names()
    
    with mic as source:
        audio = r.listen(source)
    
    
    command = str(r.recognize_google(audio))
    print(command)
    
    
    "-----Testing of both-----"
    
    if command=='uplift':
        mouse.wheel(4)
    
    if command=='down':
        mouse.wheel(-4)
    
    










