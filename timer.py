# for timer
import threading
from tkinter import dialog
import winsound  # use winows sound system
import time  # show currently running time + rounds
import keyboard  # hotkeys

import tkinter as tk  # for GUI

#make click-through -> need windows flags
import win32gui
import win32con

# make onefile possible
import os
import shutil
import sys

# controls from json file
import json

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def get_controls_path():
    return os.path.join(get_app_dir(), 'controls.json')


def ensure_controls_file():
    controls_path = get_controls_path()
    if not os.path.exists(controls_path):
        source_path = resource_path('controls.json')
        if os.path.exists(source_path):
            shutil.copyfile(source_path, controls_path)
    return controls_path


with open(ensure_controls_file(), 'r', encoding='utf-8') as f:
    controls = json.load(f)


start_time = None
active_timers = []
keyboard_hooks = []
rounds = 0
current_timer_length = 30

hidden = False
control_dialog_open = False
sound_on = True

def get_normal_name(key):
    # Map locale-specific keys to their standard equivalents for displaying in GUI
    key_map = {
        "odiaeresis": "ö",
        "udiaeresis": "ü",
        "ssharp": "ß",
        "adiaeresis": "ä"
    }
    return key_map.get(key, key)

# timer manager, starts timers, restarts itself after 30s (or custom time if provided)
def ability_timer(fulltime=30):
    if start_time is None:
        return
    
    warning_time = max(10, fulltime - 10)  # warning 10s before end
    
    t1 = threading.Timer(warning_time, lambda: root.after(0, lambda: notify(1)))
    t2 = threading.Timer(fulltime, lambda: root.after(0, lambda: notify(3)))
    t3 = threading.Timer(fulltime, lambda: root.after(0, update_rounds))
    t4 = threading.Timer(fulltime, lambda: ability_timer(30))  # always restart with 30s
    active_timers.extend([t1, t2, t3, t4])
    t1.start()
    t2.start()
    t3.start()
    t4.start()

# play sound, if not hidden show popup additionally
def notify(nr_blinks):
    
    # play sound
    if sound_on:
        threading.Thread(target=lambda: play_sound(nr_blinks)).start()
    
    # open blink root window
    if not hidden:
        threading.Thread(target=lambda: blink(nr_blinks)).start()

def blink(nr_blinks):
    match nr_blinks:
        case 1:
            color = "#FFD768"
            canvas.config(bg=color)
            canvas.update_idletasks()
            time.sleep(1)
            canvas.config(bg=backgroundcolor)
            canvas.update_idletasks()
        case 3:
            color = "#FF8E8E"
            canvas.config(bg=color)
            canvas.update_idletasks()
            time.sleep(0.3)
            canvas.config(bg=backgroundcolor)
            canvas.update_idletasks()
            time.sleep(0.2)
            canvas.config(bg=color)
            canvas.update_idletasks()
            time.sleep(0.3)
            canvas.config(bg=backgroundcolor)
            canvas.update_idletasks()
            time.sleep(0.2)
            canvas.config(bg=color)
            canvas.update_idletasks()
            time.sleep(0.7)
            canvas.config(bg=backgroundcolor)
            canvas.update_idletasks()
        case _:
            color = "white"
    


# cancel all active timers
def cancel_timers():
    for timer in active_timers:
        try:
            timer.cancel()
        except Exception:
            pass
    active_timers.clear()

# unregister all keyboard hooks
def unregister_hotkeys():
    for hook in keyboard_hooks:
        try:
            keyboard.unhook(hook)
        except Exception:
            pass
    keyboard_hooks.clear()

# cleanup before exiting
def cleanup():
    cancel_timers()
    unregister_hotkeys()
    try:
        if root.winfo_exists():
            root.destroy()
    except Exception:
        pass

# update time left label every second
def update_time_left():
    if start_time is None:
        canvas.itemconfig(time_label, text="Timer Stopped")
        return
    elapsed = int(time.time() - start_time)
    seconds = current_timer_length - (elapsed % current_timer_length)
    if seconds == current_timer_length:
        seconds = 0
    canvas.itemconfig(time_label, text=f"Time left: {seconds:02d}s")
    root.after(1000, update_time_left)

# increment rounds and update label
def update_rounds():
    global rounds
    rounds += 1
    canvas.itemconfig(rounds_label, text=f"Rounds: {rounds}")

# start timers
def start_timers():
    global start_time, current_timer_length
    if start_time is None:
        start_time = time.time()
        current_timer_length = 30
        #button.config(text="Stop Timer", command=stop_timers)
        canvas.itemconfig(startstop_label, text=f"Press {get_normal_name(controls['startstop'])} to stop")
        update_time_left()
        ability_timer(30)  # start with normal 30s

# stop timers
def stop_timers():
    global start_time
    start_time = None
    cancel_timers()
    #übutton.config(text="Start Timer", command=start_timers)
    canvas.itemconfig(startstop_label, text=f"Press {get_normal_name(controls['startstop'])} to start")
    canvas.itemconfig(time_label, text="Timer Stopped")
    canvas.itemconfig(rounds_label, text="Rounds: 0")
    global rounds
    rounds = 0

# toggle timers with hotkey
def toggle_timers():
    if start_time is None:
        start_timers()
    else:
        stop_timers()

# toggle visibility with hotkey
def toggle_visibility():
    global hidden
    hidden = not hidden
    if hidden:
        root.withdraw()  # hide window
    else:
        root.deiconify()  # show window
        root.lift()  # bring to front but don't steal focus
        root.attributes('-topmost', True)  # ensure it stays on top

# register hotkeys for start/stop and toggle visibility
def register_hotkey():
    safe_register_key(controls['startstop'], toggle_timers)
    safe_register_key(controls['visibility'], toggle_visibility)
    safe_register_key(controls['clickthrough'], lambda: toggle_click_through(root.attributes("-alpha") == 1))
    safe_register_key(controls['exit'], cleanup)
    safe_register_key(controls['change_controls'], change_controls)
    safe_register_key(controls['sound'], toggle_sound)
    safe_register_key(controls['timercustom'], timercustom)

def timercustom():
    global start_time, current_timer_length
    # cancel current timers
    cancel_timers()
    
    # get custom time from controls (default to 40 if not set)
    custom_time = int(controls.get('custom_time', 40))
    current_timer_length = custom_time
    
    # start custom timer
    start_time = time.time()
    canvas.itemconfig(startstop_label, text=f"Press {get_normal_name(controls['startstop'])} to stop")
    update_time_left()
    
    # schedule notifications and round update for custom timer
    warning_time = max(0, custom_time - 10)  # warning 10s before end
    t1 = threading.Timer(warning_time, lambda: root.after(0, lambda: notify(1)))
    t2 = threading.Timer(custom_time, lambda: root.after(0, lambda: notify(3)))
    t3 = threading.Timer(custom_time, lambda: root.after(0, update_rounds))
    t4 = threading.Timer(custom_time, lambda: root.after(0, start_normal_timer))  # after custom, switch back to normal
    active_timers.extend([t1, t2, t3, t4])
    t1.start()
    t2.start()
    t3.start()
    t4.start()

def start_normal_timer():
    global start_time, current_timer_length
    # switch back to normal 30s timer
    start_time = time.time()
    current_timer_length = 30
    ability_timer(30)

def toggle_sound():
    global sound_on
    sound_on = not sound_on
    canvas.itemconfig(sound_label, text=f"Press {get_normal_name(controls['sound'])} to turn sound {'on' if not sound_on else 'off'}")

# helper to register a hotkey without failing on locale-specific keys
def safe_register_key(key, action):
    def handler(event=None):        
        if control_dialog_open:  # ignore hotkeys if dialog is open
            return
        try:
            if root.winfo_exists():
                root.after(0, action)
        except RuntimeError:
            pass
        except Exception:
            pass

    try:
        hook = keyboard.on_press_key(key, handler)
        keyboard_hooks.append(hook)
        #print("Registered hotkey:", key)
    except ValueError:
        hook = keyboard.on_press(lambda event: handler(event) if event.name == key else None)
        keyboard_hooks.append(hook)
        print("Registered hotkey with fallback:", key)

# play sound, different sound for 10s warning and actual ability
def play_sound(nr_blinks):
    match nr_blinks:
        case 1:
            winsound.Beep(900, 1000)  # 900 Hz for 1000 ms
        case 3:
            #winsound.MessageBeep()
            winsound.Beep(900, 500)
            winsound.Beep(900, 500)
            winsound.Beep(900, 700)
        case _:
            pass

def toggle_click_through(click_through):
    # set windows flags for click-through
    try:
        hwnd = win32gui.FindWindow(None, root.title())
        if not hwnd:
            print("ERROR: Fenster nicht gefunden. Titel:", root.title())
            return
        
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if click_through:  # enable click-through
            new_ex_style = ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            show_info(False)
            disable_control("change_controls")  # disable control change while click-through enabled

        else:  # disable click-through
            new_ex_style = ex_style & ~(win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
            show_info(True)
            enable_control("change_controls", change_controls)  # enable control change while click-through disabled

        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_ex_style)

        # tkinter setup
        root.attributes("-alpha", 0.8 if click_through else 1)  # slightly transparent
        root.update_idletasks()
    except Exception as e:
        print(f"ERROR in toggle_click_through: {e}")

def disable_control(control_name):
    # unregister hotkey for control
    try:
        if control_name in controls:
            key = controls[control_name]
            keyboard.unhook_key(key)
    except Exception as e:
        print(f"ERROR in disable_control: {e}")

def enable_control(control_name, action):
    # re-register hotkey for control
    try:
        if control_name in controls:
            key = controls[control_name]
            safe_register_key(key, action)
            print(f"Enabled control: {control_name} ({key})")
    except Exception as e:
        print(f"ERROR in enable_control: {e}")

def show_info(shown):
    canvas.itemconfig(startstop_label, state="normal" if shown else "hidden")
    canvas.itemconfig(visibility_label, state="normal" if shown else "hidden")
    canvas.itemconfig(clickthrough_label, state="normal" if shown else "hidden")
    canvas.itemconfig(exit_label, state="normal" if shown else "hidden")
    canvas.itemconfig(change_controls_label, state="normal" if shown else "hidden")
    canvas.itemconfig(sound_label, state="normal" if shown else "hidden")
    canvas.itemconfig(timercustom_label, state="normal" if shown else "hidden")
    if shown:
        root.geometry("180x290")
    else:
        root.geometry("180x80")

def change_controls():
    global control_dialog_open
    # open a simple input dialog to change controls
    dialog = tk.Toplevel(root)
    dialog.title("Change Controls")
    control_dialog_open = True

    def on_dialog_close():
        global dialog_open
        dialog_open = False
        dialog.destroy()
    
    dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)

    dialog.attributes('-topmost', True)  # always on top
    

    # dialog window next to root window (left side)
    dialog.geometry(f"255x220+{root.winfo_x() - 280}+{root.winfo_y()}")

    tk.Label(dialog, text="Start/Stop Timer:").grid(row=0, column=0, sticky="e")
    startstop_entry = tk.Entry(dialog)
    startstop_entry.insert(0, controls['startstop'])
    startstop_entry.grid(row=0, column=1)

    tk.Label(dialog, text="Toggle Visibility:").grid(row=1, column=0, sticky="e")
    visibility_entry = tk.Entry(dialog)
    visibility_entry.insert(0, controls['visibility'])
    visibility_entry.grid(row=1, column=1)

    tk.Label(dialog, text="Toggle Click-Through:").grid(row=2, column=0, sticky="e")
    clickthrough_entry = tk.Entry(dialog)
    clickthrough_entry.insert(0, controls['clickthrough'])
    clickthrough_entry.grid(row=2, column=1)

    tk.Label(dialog, text="Exit App:").grid(row=3, column=0, sticky="e")
    exit_entry = tk.Entry(dialog)
    exit_entry.insert(0, controls['exit'])
    exit_entry.grid(row=3, column=1)

    tk.Label(dialog, text="Change Controls:").grid(row=4, column=0, sticky="e")
    change_controls_entry = tk.Entry(dialog)
    change_controls_entry.insert(0, controls['change_controls'])
    change_controls_entry.grid(row=4, column=1)

    tk.Label(dialog, text="Sound On/Off:").grid(row=5, column=0, sticky="e")
    sound_entry = tk.Entry(dialog)
    sound_entry.insert(0, controls['sound'])
    sound_entry.grid(row=5, column=1)

    tk.Label(dialog, text="Custom Timer:").grid(row=6, column=0, sticky="e")
    timercustom_entry = tk.Entry(dialog)
    timercustom_entry.insert(0, controls['timercustom'])
    timercustom_entry.grid(row=6, column=1)

    tk.Label(dialog, text="Custom Time (s):").grid(row=7, column=0, sticky="e")
    custom_time_entry = tk.Entry(dialog)
    custom_time_entry.insert(0, controls.get('custom_time', '40'))
    custom_time_entry.grid(row=7, column=1)

    def save_controls():
        global control_dialog_open
        new_controls = {
            "startstop": startstop_entry.get(),
            "visibility": visibility_entry.get(),
            "clickthrough": clickthrough_entry.get(),
            "exit": exit_entry.get(),
            "change_controls": change_controls_entry.get(),
            "sound": sound_entry.get(),
            "timercustom": timercustom_entry.get(),
            "custom_time": custom_time_entry.get()
        }
        controls_path = get_controls_path()
        with open(controls_path, "w", encoding='utf-8') as f:
            json.dump(new_controls, f, indent=4)

        control_dialog_open = False
        dialog.destroy()
        
        # avoid restarting app
        unregister_hotkeys()
        controls.update(new_controls)
        register_hotkey()
        change_labels()

    save_button = tk.Button(dialog, text="Save", command=save_controls, width=20)
    save_button.grid(row=9, column=0, columnspan=2, pady=10)

def change_labels():
    canvas.itemconfig(startstop_label, text=f"Press {get_normal_name(controls['startstop'])} to {'stop' if start_time else 'start'}")
    canvas.itemconfig(visibility_label, text=f"Press {get_normal_name(controls['visibility'])} to toggle visibility")
    canvas.itemconfig(clickthrough_label, text=f"Press {get_normal_name(controls['clickthrough'])} to toggle click-through")
    canvas.itemconfig(exit_label, text=f"Press {get_normal_name(controls['exit'])} to exit")
    canvas.itemconfig(change_controls_label, text=f"Press {get_normal_name(controls['change_controls'])} to change controls")
    canvas.itemconfig(sound_label, text=f"Press {get_normal_name(controls['sound'])} to turn sound {'on' if not sound_on else 'off'}")
    canvas.itemconfig(timercustom_label, text=f"Press {get_normal_name(controls['timercustom'])} for {controls.get('custom_time', '40')}s timer")
    

# --- main ---
root = tk.Tk()  # tk-mainmenu

# window setup
backgroundcolor = "white"
root.title("Ability Timer")
root.resizable(False, False)
root.config(bg=backgroundcolor)
root.attributes("-topmost", True, "-alpha", 1)  # always on top

root.overrideredirect(True)
canvas = tk.Canvas(root, width=180, height=290, bg=backgroundcolor, highlightthickness=0)
canvas.pack(fill="both", expand=True)

# labels
time_label = canvas.create_text(90, 30, text="Time left: 00s", font=("Arial", 14), fill="black", anchor="center", justify="center")
rounds_label = canvas.create_text(90, 60, text="Rounds: 0", font=("Arial", 12), fill="black", anchor="center", justify="center")
startstop_label = canvas.create_text(90, 90, text=f"Press {get_normal_name(controls['startstop'])} to start", font=("Arial", 10), fill="black", anchor="center", justify="center")
visibility_label = canvas.create_text(90, 120, text=f"Press {get_normal_name(controls['visibility'])} to toggle visibility", font=("Arial", 10), fill="black", anchor="center", justify="center")
clickthrough_label = canvas.create_text(90, 150, text=f"Press {get_normal_name(controls['clickthrough'])} to toggle click-through", font=("Arial", 10), fill="black", anchor="center", justify="center")
exit_label = canvas.create_text(90, 180, text=f"Press {get_normal_name(controls['exit'])} to exit", font=("Arial", 10), fill="black", anchor="center", justify="center")
change_controls_label = canvas.create_text(90, 210, text=f"Press {get_normal_name(controls['change_controls'])} to change controls", font=("Arial", 10), fill="black", anchor="center", justify="center")
sound_label = canvas.create_text(90, 240, text=f"Press {get_normal_name(controls['sound'])} to turn sound {'on' if not sound_on else 'off'}", font=("Arial", 10), fill="black", anchor="center", justify="center")
timercustom_label = canvas.create_text(90, 270, text=f"Press {get_normal_name(controls['timercustom'])} to start custom timer", font=("Arial", 10), fill="black", anchor="center", justify="center")
#button = tk.Button(root, text="Start Timer", command=start_timers)  # button in main menu to start timer
#button.pack(pady=(0, 10))

register_hotkey()

# top right corner
root.update_idletasks()
root_width = root.winfo_width()
root_height = root.winfo_height()
screen_width = root.winfo_screenwidth()
x = screen_width - root_width - 10
y = 50
root.geometry(f"+{x}+{y}")
root.protocol("WM_DELETE_WINDOW", cleanup)

root.mainloop()
