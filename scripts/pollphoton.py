import socket
import subprocess
import time
import argparse
import tkinter as tk
from tkinter import filedialog
from PyQt5.QtWidgets import QApplication, QFileDialog
from photonmmu_pump import run_stepper as pumps

import RPi.GPIO as GPIO

# Qt File Dialog Setup
def open_file_dialog():
    app = QApplication([])
    f_dialog = QFileDialog()
    f_path = f_dialog.getOpenFileName()
    return f_path[0]


# GPIO SET
led = 22
GPIO.setmode(GPIO.BCM)
GPIO.setup(led, GPIO.OUT)

# define the IP address and port number to connect to
IP_ADDRESS = '192.168.4.2'
PORT_NUMBER = 6000

# create a socket object
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connect to the server
client_socket.connect((IP_ADDRESS, PORT_NUMBER))

# prompt the user to enter the script name and arguments
p_name = 'gopause'
r_name = 'goresume'
s_name = 'getstatus'
f_name = 'getfile'
# build the command to execute the script with arguments
setup_command = "python3 monox.py" ' -i ' + IP_ADDRESS +  ' -c '
status_command = setup_command + s_name
pause_command = setup_command + p_name
resume_command = setup_command + r_name
file_command = setup_command + f_name
hacked_command = setup_command + 'getmode'
# send the command to the server
client_socket.send(status_command.encode())

# receive the response from the server
response = client_socket.recv(1024).decode()
print(response)
data = response.split(',')
#print('Received response: ', response)
layernum_search = '15'

# client_socket.sendall(resume_command.encode())
# response = client_socket.recv(1024).decode()
# print(response)

# Create root window
root = tk.Tk()
root.withdraw()

# open the file dialog box and get the path file
file_path = open_file_dialog()
layerlist = []
# Open the file and read
with open(file_path, 'r') as f:
    #layerfile = f.read()
    for line in f:
        layerlist.append(line.strip().split(':'))
        print(layerlist)
        newlist = [[item.split(',')[0], int(item.split(',')[1])] for sublist in layerlist for item in sublist]


print(layerlist)
print (newlist)
start_index = 0

max_retries = 10
wait = 5
while True:
    try:
        client_socket.send(status_command.encode())
        # receive the response from the server
        response = client_socket.recv(1024).decode()
        # print(response)
        data = response.split(',')
        #print(data[1])
        #print("Current Layer: ",data[15])
        print("Next Layer Change: ", newlist)
        if (data[1] == 'pause'):
            client_socket.sendall(resume_command.encode())
        elif (data[1] == 'ERROR1'):
            time.sleep(3)
        elif (data[1] == 'stop\r\n'):
            time.sleep(5)

    except IndexError:
        print('All changes completed... Printing Normally')
        break
    except socket.error as e:
        if e.errno == 104:
            print(f"Connection reset by peer retrying in {wait} seconds...")
            time.sleep(wait)
            # create a socket object
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # connect to the server
            client_socket.connect((IP_ADDRESS, PORT_NUMBER))
        else: 
            raise

    try:
        time.sleep(3)
        client_socket.sendall(status_command.encode())
        response = client_socket.recv(1024).decode()
        newdata = response.split(',')
        try:
                converted_layer = int(newdata[5])
        except ValueError:
                print(f"Could not convert '{converted_layer}' to an integer")
                continue
        print("Searching...")
        print("start index: ",start_index)
        print("layerlist: ",(newlist))
        print("layerchange num", (newlist[start_index][1]))
        print("Current Layer", (converted_layer))
        print("lenlist",len(newlist))
        
        if start_index<len(newlist):
            if newlist[start_index][1] == converted_layer:
                print("FOUND")
                
                client_socket.sendall(pause_command.encode())
                time.sleep(3)
                GPIO.output(led, GPIO.HIGH)
                
                #print("GPIO: ",GPIO.input(led))\
                
                print("Draining Material... Please Wait")
                #pumps('D', 'R', 250)
                pumps('D', 'F', 10)
                GPIO.output(led, GPIO.LOW)
                print("GPIO: ", GPIO.input(led))
                print("Done Drain")
                print("Changing Material... Please Wait")
                #pumps(newlist[start_index][0], 'F', 225)
                pumps(newlist[start_index][0], 'F', 10)
                time.sleep(10)
                try:
                        client_socket.sendall(resume_command.encode())
                except socket.error as e:
                        if e.errno == 104:
                            print(f"Connection reset by peer retrying in {wait} seconds...")
                            time.sleep(wait)
                            # create a socket object
                            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                            # connect to the server
                            client_socket.connect((IP_ADDRESS, PORT_NUMBER))                
                print("Changed... Resuming Print")
                start_index += 1
        else:
                sys.exit()
    except IndexError:
        print('App interference')
        print(newdata)
        pass
    except socket.error as e:
        if e.errno == 104:
            print(f"Connection reset by peer retrying in {wait} seconds...")
            time.sleep(wait)
            # create a socket object
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # connect to the server
            client_socket.connect((IP_ADDRESS, PORT_NUMBER))
        else:
            raise

    time.sleep(3)

    #client_socket.sendall(status_command.encode())
    #print("are you blocking me")

# close the socket
client_socket.close()
