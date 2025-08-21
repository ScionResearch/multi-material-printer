import tkinter as tk
from tkinter import messagebox
import subprocess
import re
import signal
import threading

# Global variables
running_process = None

# Function to run a script
def run_script(script_name, light):
    global running_process

    if running_process and running_process.poll() is None: 
        running_process.terminate()

    running_process = subprocess.Popen(["python3", script_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def capture_output():
        while running_process.poll() is None:
            line = running_process.stdout.readline()
            terminal_output.insert(tk.END, line.decode())
        light.configure(bg="green", relief=tk.FLAT)
        window.after(3000, lambda: reset_light(light))  # Reset light to red after 3000 milliseconds (3 seconds)

    terminal_output.delete("1.0", tk.END)
    light.configure(bg="yellow", relief=tk.FLAT)
    thread = threading.Thread(target=capture_output)
    thread.start()

# Function to reset the light to red
def reset_light(light):
    light.configure(bg="red", relief=tk.RAISED)

# Function to interrupt running scripts
def interrupt_scripts():
    global running_process
    if running_process and running_process.poll() is None:
        running_process.send_signal(signal.SIGINT)
        for light in lights:
            reset_light(light)

# Function to save input text
def save_input_text():
    user_input = input_entry.get()
    pattern = r'^\d+,[a-zA-Z];\s*$'
    if re.match(pattern, user_input):
        with open("layerlines.txt", "w") as file:
            file.write(user_input)
        input_entry.delete(0, tk.END)
        draw_tick()
        window.after(3000, clear_tick)
    else:
        messagebox.showerror("Invalid Format", "Please enter the input in the required format: number,letter;")

# Function to draw the tick symbol
def draw_tick():
    tick_box.itemconfig(tick_line, state=tk.NORMAL)
    tick_box.itemconfig(tick_text, state=tk.NORMAL)

# Function to clear the tick symbol
def clear_tick():
    tick_box.itemconfig(tick_line, state=tk.HIDDEN)
    tick_box.itemconfig(tick_text, state=tk.HIDDEN)

# Create the main window
window = tk.Tk()
window.title("Hardware Control GUI")

# Create the buttons and lights
button_data = [
    ("Script 1", "photonmmu_pump.py"),
    ("Script 2", "pollphoton.py"),
    ("Script 3", "script_3.py")
]

light_size = 40
lights = []
for i, (button_text, script_name) in enumerate(button_data):
    light = tk.Button(
        window,
        text=button_text,
        command=lambda script_name=script_name, light=light: run_script(script_name, light),
        width=light_size,
        height=light_size,
        relief=tk.FLAT,
        bg="red",
        activebackground="red"
    )
    light.grid(row=1, column=i, padx=10, pady=10)
    lights.append(light)
    
# Create the terminal output
terminal_output = tk.Text(window)
terminal_output.configure(state='disabled')
terminal_output.grid(row=2, column=0, columnspan=len(button_data), padx=10, pady=10)

# Create the input frame
input_frame = tk.Frame(window)
input_frame.grid(row=3, column=0, columnspan=len(button_data), padx=10, pady=10)

# Create the input line and submit button
input_label = tk.Label(input_frame, text="Input:")
input_label.grid(row=0, column=0)

input_entry = tk.Entry(input_frame, width=30)
input_entry.grid(row=0, column=1)

submit_button = tk.Button(input_frame, text="Submit", command=save_input_text)
submit_button.grid(row=0, column=2)

# Create the tick box
tick_box = tk.Canvas(input_frame, width=30, height=30, bg="white", highlightthickness=0)
tick_box.grid(row=0, column=3, padx=5, pady=5)

tick_line = tick_box.create_line(5, 15, 10, 20, 20, 10, width=3, capstyle=tk.ROUND, state=tk.HIDDEN)
tick_text = tick_box.create_text(25, 13, text="✓", font=("Arial", 16, "bold"), state=tk.HIDDEN)

# Create the interrupt button
interrupt_button = tk.Button(window, text="Interrupt", command=interrupt_scripts)
interrupt_button.grid(row=4, column=0, columnspan=len(button_data), padx=10, pady=10)

# Configure row and column weights
for i in range(len(button_data)):
    window.grid_columnconfigure(i, weight=1)
window.grid_rowconfigure(2, weight=1)

# Start the main loop
window.mainloop()
