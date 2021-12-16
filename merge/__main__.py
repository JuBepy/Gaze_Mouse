import logging.handlers
import os
import sys
from pathlib import Path

### Libraries for threading functions
import threading 
from queue import Queue

### Libraries for the mouse and speech recognition
import mouse
import speech_recognition as sr


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    meipass = Path(sys._MEIPASS)
    lib_path = next(meipass.glob("*glfw*"), None)
    os.environ["PYGLFW_LIBRARY"] = str(lib_path)

from .models import Host_Controller
from .overlay import GazeOverlay
from .texture import PITextureController
from .ui import HostViewController
from .window import Window

def audio_recognition (buffer_mouse_click, buffer_mouse_option):
    
    command = ''
    
    while True:
        
        r = sr.Recognizer()
        mic = sr.Microphone()
        sr.Microphone.list_microphone_names()
        
        with mic as source:
            audio = r.listen(source)
    
        command = str(r.recognize_google(audio))
        #print(command)
        
        if command == 'select':
            buffer_mouse_click.put("1")
            
        if command == 'option':
            buffer_mouse_option.put("1")
    




def main(buffer_mouse_click, buffer_mouse_option):
    
    log_path = Path.home() / "pi_monitor_settings" / "pi_monitor.log"
    log_path.parent.mkdir(exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(log_path, mode="w", backupCount=30),
    ]
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=handlers,
        style="{",
        format="{asctime} [{levelname}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    
 
    try:
        host_controller = Host_Controller()

        # frame observer
        texture_controller = PITextureController()
        host_controller.add_observer("on_host_linked", texture_controller.reset)
        host_controller.add_observer("on_recent_frame", texture_controller.update)

        gaze_overlay = GazeOverlay()
        
        # Ajouts Cyrille
        # coordinates = np.array (gaze_overlay._recent_gaze())
        # mouse.move(coordinates[0], coordinates[1], absolute=True, duration=0)
        
        if buffer_mouse_click.empty() == False:
            buffer_mouse_click.get()
            print("[LEFT CLICK]")
            mouse.click("left")
        
        if buffer_mouse_option.empty() == False:
            buffer_mouse_option.get()
            print("[RIGHT CLICK]")
            mouse.click("right")
            
        host_controller.add_observer("on_recent_gaze", gaze_overlay.update)
        
        
        win = Window(
            texture_controller,
            frame_rate=60.0,
            callables=[
                host_controller.poll_events,
                host_controller.fetch_recent_data,
                gaze_overlay.draw,
                gaze_overlay.mouse_control,
            ],
        )
        win.open()
        host_view_controller = HostViewController(
            gui_parent=win.quickbar, controller=host_controller
        )
        
    
        win.run_event_loop()
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.exception("Exception occured!")
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                handler.doRollover()
    finally:
        win.close()
        host_controller.cleanup()
        host_view_controller.cleanup()
        logging.shutdown()


if __name__ == "__main__":
    
     
    ### Threading ###
    
    buffer_mouse_click = Queue() # buffer click gauche souris
    buffer_mouse_option = Queue() # buffer click droit souris
    
    thr = threading.Thread(target = audio_recognition, args = (buffer_mouse_click, buffer_mouse_option,) )
    thr.start()
    
    
    main(buffer_mouse_click, buffer_mouse_option)
