import tkinter as tk
import subprocess
import re

def run_script(script_name, light):
    output = subprocess.check_output(["python3", script_name])
    terminal_output.insert(tk.END, output)
    light.configure(bg="green", relief=tk.SUNKEN)

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
        tk.messagebox.showerror("Invalid Format", "Please enter the input in the required format: number,letter;")

def draw_tick():
    tick_box.itemconfig(tick_line, state=tk.NORMAL)
    tick_box.itemconfig(tick_text, state=tk.NORMAL)

def clear_tick():
    tick_box.itemconfig(tick_line, state=tk.HIDDEN)
    tick_box.itemconfig(tick_text, state=tk.HIDDEN)

# Create the main window
window = tk.Tk()

# Create the buttons and lights
button_data = [
    ("Script 1", "photonmmu_pump.py"),
    ("Script 2", "pollphoton.py"),
    ("Script 3", "script_3.py")
]

light_size = 40
lights = []
for i, (button_text, script_name) in enumerate(button_data):
    light = tk.Canvas(window, width=light_size, height=light_size, bg="red", highlightthickness=0, relief=tk.RAISED)
    light.grid(row=1, column=i, padx=10, pady=10)
    lights.append(light)

    button = tk.Button(window, text=button_text, command=lambda script_name=script_name, light=light: run_script(script_name, light))
    button.grid(row=0, column=i, padx=10, pady=10)

# Create the terminal output
terminal_output = tk.Text(window)
terminal_output.configure(state='disabled')
terminal_output.grid(row=2, column=0, columnspan=len(button_data), padx=10, pady=10)

# Create the input line and submit button
input_frame = tk.Frame(window)
input_label = tk.Label(input_frame, text="Input:")
input_entry = tk.Entry(input_frame, width=30)

submit_button = tk.Button(input_frame, text="Submit", command=save_input_text)

# Create the tick box
tick_box = tk.Canvas(input_frame, width=30, height=30, bg="white", highlightthickness=0)
tick_line = tick_box.create_line(5, 15, 10, 20, 20, 10, width=3, capstyle=tk.ROUND, state=tk.HIDDEN)
tick_text = tick_box.create_text(25, 13, text="✓", font=("Arial", 16, "bold"), state=tk.HIDDEN)

# Grid layout
for i in range(len(button_data)):
    window.grid_columnconfigure(i, weight=1)

input_frame.grid(row=3, column=0, columnspan=len(button_data), padx=10, pady=10)
input_label.grid(row=0, column=0)
input_entry.grid(row=0, column=1)
submit_button.grid(row=0, column=2)
tick_box.grid(row=0, column=3, padx=5, pady=5)

# Start the main loop
window.mainloop()
