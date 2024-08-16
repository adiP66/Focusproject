import os
import sys
import ctypes
import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
import time
import winsound
import cv2
import numpy as np


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if sys.version_info[0] == 3 and sys.version_info[1] >= 5:
        params = ' '.join(['"' + arg + '"' for arg in sys.argv])
    else:
        params = ' '.join(['"' + arg + '"' for arg in '\"' + sys.executable + '\"'])
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to elevate process: {e}")

def block_websites(websites):
    hosts_path = r'C:\Windows\System32\drivers\etc\hosts'
    redirect = '127.0.0.1'

    try:
        with open(hosts_path, 'r+') as file:
            content = file.read()
            for website in websites:
                if website not in content:
                    file.write(redirect + ' ' + website + '\n')
        messagebox.showinfo("Success", "Websites blocked successfully.")
    except PermissionError:
        messagebox.showerror("Error", "Permission denied. Please run the script as an administrator.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def unblock_websites(websites):
    hosts_path = r'C:\Windows\System32\drivers\etc\hosts'

    try:
        with open(hosts_path, 'r') as file:
            lines = file.readlines()

        with open(hosts_path, 'w') as file:
            for line in lines:
                if not any(website in line for website in websites):
                    file.write(line)

        messagebox.showinfo("Success", "Websites unblocked successfully.")
    except PermissionError:
        messagebox.showerror("Error", "Permission denied. Please run the script as an administrator.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def start_timer():
    global timer_running, blocked_websites, stop_button
    blocked_websites = website_entry.get().split(',')
    blocked_websites = [website.strip() for website in blocked_websites]
    timer_running = True
    timer_thread = threading.Thread(target=run_timer)
    timer_thread.start()

    # Show the stop button
    stop_button.pack(pady=10)

    # Start the camera thread
    camera_thread = threading.Thread(target=start_camera)
    camera_thread.start()

def run_timer():
    global timer_running
    duration = int(timer_entry.get()) * 60
    start_time = time.time()
    block_websites(blocked_websites)

    while timer_running and (time.time() - start_time < duration):
        remaining_time = duration - int(time.time() - start_time)
        timer_label.config(text=f"Time remaining: {remaining_time // 60} minutes {remaining_time % 60} seconds")
        root.update()
        time.sleep(1)

    if timer_running:
        winsound.Beep(1000, 1000)
        unblock_websites(blocked_websites)
        messagebox.showinfo("Timer", "Time's up! Websites unblocked.")
        timer_running = False
        website_entry.delete(0, tk.END)
        stop_button.pack_forget()

def stop_timer():
    global timer_running
    timer_running = False
    unblock_websites(blocked_websites)
    messagebox.showinfo("Timer", "Timer stopped. Websites unblocked.")
    website_entry.delete(0, tk.END)
    stop_button.pack_forget()

def on_closing():
    if timer_running:
        messagebox.showwarning("Warning", "You cannot close the application while the timer is running.")
    else:
        root.destroy()

def start_camera():
    global timer_running
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Paths to the model files
    modelFile = "res10_300x300_ssd_iter_140000_fp16.caffemodel"
    configFile = "deploy.prototxt"
    
    if not os.path.exists(modelFile) or not os.path.exists(configFile):
        messagebox.showerror("Error", "Model files not found. Ensure 'deploy.prototxt' and 'res10_300x300_ssd_iter_140000_fp16.caffemodel' are in the correct directory.")
        return

    net = cv2.dnn.readNetFromCaffe(configFile, modelFile)
    
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        messagebox.showerror("Error", "Failed to open camera.")
        return

    no_face_count = 0
    grace_period_seconds = 10  # Time window for user to come back
    grace_start_time = None

    while timer_running:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
        net.setInput(blob)
        detections = net.forward()
        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:
                box = detections[0, 0, i, 3:7] * np.array([frame.shape[1], frame.shape[0], frame.shape[1], frame.shape[0]])
                (x, y, x1, y1) = box.astype("int")
                faces.append((x, y, x1 - x, y1 - y))

        if len(faces) == 0:
            if grace_start_time is None:
                grace_start_time = time.time()
            elif time.time() - grace_start_time >= grace_period_seconds:
                timer_running = False
                unblock_websites(blocked_websites)
                messagebox.showinfo("Timer", "User not detected. Timer stopped. Websites unblocked.")
                website_entry.delete(0, tk.END)
                stop_button.pack_forget()
                break
        else:
            grace_start_time = None

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

        cv2.imshow('Camera', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()



if __name__ == "__main__":
    if is_admin():
        root = tk.Tk()
        root.title("Productivity Timer")
        root.protocol("WM_DELETE_WINDOW", on_closing)

        tk.Label(root, text="Enter websites to block (comma-separated):").pack(pady=5)
        website_entry = tk.Entry(root, width=50)
        website_entry.pack(pady=5)

        tk.Label(root, text="Enter timer duration (minutes):").pack(pady=5)
        timer_entry = tk.Entry(root, width=50)
        timer_entry.pack(pady=5)

        tk.Button(root, text="Start Timer", command=start_timer).pack(pady=10)

        stop_button = tk.Button(root, text="Stop Timer", command=stop_timer)

        timer_label = tk.Label(root, text="Time remaining: 0 minutes 0 seconds")
        timer_label.pack(pady=5)

        root.mainloop()
    else:
        run_as_admin()
