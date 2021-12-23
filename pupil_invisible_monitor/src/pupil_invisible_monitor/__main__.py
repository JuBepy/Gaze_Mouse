import logging.handlers
import os
import sys
from pathlib import Path

### Libraries for threading functions
import threading 
from queue import Queue

### Libraries for the mouse and speech recognition
import mouse
import sounddevice as sd
import vosk
import argparse
import json


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    meipass = Path(sys._MEIPASS)
    lib_path = next(meipass.glob("*glfw*"), None)
    os.environ["PYGLFW_LIBRARY"] = str(lib_path)

from .models import Host_Controller
from .overlay import GazeOverlay
from .texture import PITextureController
from .ui import HostViewController
from .window import Window


### Function that runs in parallel with the video processing
def audio_recognition (args, q_vosk, model, dump_fn):
        
   
    with sd.RawInputStream(samplerate=args.samplerate, blocksize = 8000, device=args.device, dtype='int16',
                        channels=1, callback=callback):
      

        rec = vosk.KaldiRecognizer(model, args.samplerate)
        while True:
            data = q_vosk.get()
            if rec.AcceptWaveform(data):
                
                dictResult = json.loads(rec.Result())
                
                # Keywords for the mouse actions
                if "sélection" in dictResult.get("text"):
                      print("[LEFT CLICK]")
                      mouse.click("left")
                 
                if "option" in dictResult.get("text"):        
                    print("[RIGHT CLICK]")
                    mouse.click("right")
                    
                if "montée" in dictResult.get("text"):
                    print("[UP]")
                    mouse.wheel(1)
                    
                if "descente" in dictResult.get("text"):
                    print("[DOWN]")
                    mouse.wheel(-1)
                    
            else:
                pass
               # print(rec.PartialResult())
            if dump_fn is not None:
                dump_fn.write(data)
   

if __name__ == "__main__":
    
    
    q_vosk = Queue()

    def int_or_str(text):
        """Helper function for argument parsing."""
        try:
            return int(text)
        except ValueError:
            return text
    
    def callback(indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        q_vosk.put(bytes(indata))
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '-l', '--list-devices', action='store_true',
        help='show list of audio devices and exit')
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parser])
    parser.add_argument(
        '-f', '--filename', type=str, metavar='FILENAME',
        help='audio file to store recording to')
    parser.add_argument(
        '-m', '--model', type=str, metavar='MODEL_PATH',
        help='Path to the model')
    parser.add_argument(
        '-d', '--device', type=int_or_str,
        help='input device (numeric ID or substring)')
    parser.add_argument(
        '-r', '--samplerate', type=int, help='sampling rate')
    args = parser.parse_args(remaining)
    
    
    
    if args.model is None:
        args.model = "model"
    if not os.path.exists(args.model):
        print ("Please download a model for your language from https://alphacephei.com/vosk/models")
        print ("and unpack as 'model' in the current folder.")
        parser.exit(0)
    if args.samplerate is None:
        device_info = sd.query_devices(args.device, 'input')
        # soundfile expects an int, sounddevice provides a float:
        args.samplerate = int(device_info['default_samplerate'])
    
    model = vosk.Model(args.model)
    print('MODELLLLLLLLLLLLLLLLL :'+ str(model))
    if args.filename:
        dump_fn = open(args.filename, "wb")
    else:
        dump_fn = None
        
     
    ### Threading ###
        
    thr = threading.Thread(target = audio_recognition, args = (args, q_vosk, model, dump_fn,) )
    thr.start()
    
    
       
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
        
            
        host_controller.add_observer("on_recent_gaze", gaze_overlay.update)
        
        
        win = Window(
            texture_controller,
            frame_rate=60.0,
            callables=[
                host_controller.poll_events,
                host_controller.fetch_recent_data,
                gaze_overlay.draw
             
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
