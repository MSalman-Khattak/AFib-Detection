import serial
import time
import csv
import os


# Global variable to control the cancel flag
cancel_reading = False

def read_ppg(read_duration,email):
    # Open serial connection
    ser = serial.Serial('COM6', 9600)  # Replace 'COM6' with your Arduino's port

    global cancel_reading

    start_time = time.time()
    with open('ppg_data' + email + '.csv', 'w', newline='') as csvfile:
        fieldnames = ['timestamp', 'ppg_value']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        while time.time() - start_time < read_duration:
            if cancel_reading == True:
                cancel_reading = False
                # Close serial connection
                ser.close()
                break

            ser.write(b's')  # Send command to Arduino to start reading PPG values
            time.sleep(0.05)  # Wait for a short time to allow Arduino to respond
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').rstrip()
                timestamp = time.time() - start_time  # Get current time since start in seconds
                timestamp_formatted = "{:.3f}".format(timestamp)  # Format timestamp to 3 decimal places
                writer.writerow({'timestamp': timestamp_formatted, 'ppg_value': line})

    # Close serial connection
    ser.close()

def set_cancel_flag():
    global cancel_reading
    cancel_reading = True

def remove_csv(csv_filename):
    os.remove(csv_filename)