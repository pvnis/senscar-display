import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import threading
from stats import Statistics
import ina219
import os
import subprocess
import time

# Settings for reading
VOLTAGE_READER_I2C_ADDR=0x42

# 128x32 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_bus=1, gpio=1) # setting gpio to 1 is hack to avoid platform detection

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))


class Display(object):
    
    def __init__(self):
        # Connect to the Voltage sensor
        self.ina = ina219.INA219(addr=0x42)


        
        # Connecto to the display
        self.display = Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_bus=1, gpio=1) 
        self.display.begin()
        self.display.clear()
        self.display.display()

        # Display config
        self.font = ImageFont.load_default()
        self.image = Image.new('1', (self.display.width, self.display.height))
        self.draw = ImageDraw.Draw(self.image)
        self.draw.rectangle((0, 0, self.image.width, self.image.height), outline=0, fill=0)

        self.stats_enabled = False
        self.stats_thread = None
        self.stats_interval = 5.0
        
        # Get statistics instance
        # Get instance of interface that we query
        interface = ""
        tries = 0 
        while not ("ww" in interface or "enx" in interface):
            cmd_string = "ip -4 a | grep -e 'ww' -e 'enx' | head -n1 | awk '{ print $2 }' | sed 's/://g'"
            interface  = subprocess.check_output(cmd_string, shell=True).decode('ascii').strip()
            
            self.draw.rectangle((0, 0, self.image.width, self.image.height), outline=0, fill=0)
            top = -2
            self.draw.text((20, top), "=== INIT Car ===", font=self.font, fill=255)
            self.draw.text((1, 10), "No WWAN found", font=self.font, fill=255)
            self.draw.text((1, 22), f"Got: {interface} Tries: {tries}", font=self.font, fill=255)
            self.display.image(self.image)
            self.display.display()
            print(f"No WWAN interface found, (got : {interface}) retrying...")
            tries+=1
            time.sleep(5)
        
        print("Got interface:", interface)
        self.stats = Statistics(interface)
        self.curr_show = 1

        # Start thread to measure things
        self.enable_stats()
        
    def _run_display_stats(self):
        charging = False
        while self.stats_enabled:
                
            # Prepare printout
            self.draw.rectangle((0, 0, self.image.width, self.image.height), outline=0, fill=0)
            top = -2
            self.draw.text((20, top), "=== SENS Car ===", font=self.font, fill=255)
            
            # Get states
            connected = self.stats.get_connection_state()
            signal = self.stats.get_signal_strength()
            ip = self.stats.get_ip_address()
            modem_state = self.stats.get_modem_state()

            bus_voltage = self.ina.getBusVoltage_V()        # voltage on V- (load side)
            current = self.ina.getCurrent_mA()                # current in mA
            p = (bus_voltage - 9)/3.6*100
            if(p > 100):p = 100
            if(p < 0):p = 0
            if(current < 0):current = 0
            if(current > 30):
                charging = not charging
            else:
                charging = False

            # Debug print
            # print("Connected:", connected)
            # print("Signal Strength:", signal)
            # print("IP:", ip)
            # print("CONNECTION:", modem_state)
            
            # CASE IP & CONN
            
            if self.curr_show % 3 == 0:

                # set stats headers
                top = 10
                offset = 4 * 10
                headers = ['IP', '', 'PDU', '']
                for i, header in enumerate(headers):
                    self.draw.text((i * offset + 4, top), header, font=self.font, fill=255)

                # set stats fields
                top = 22
                
                entries = [ip, "", modem_state, ""]
                for i, entry in enumerate(entries):
                    self.draw.text((i * offset + 4, top), entry, font=self.font, fill=255)

            #
            # CASE SIG & MODEM
            #
            
            if self.curr_show % 3 == 1:
                # print("SHOWING SIGNAL AND INTERFACE")
                # # set stats headers
                top = 10
                offset = 4 * 8
                headers = ['SIG', 'INTERFACE', '', '']
                for i, header in enumerate(headers):
                    self.draw.text((i * offset + 4, top), header, font=self.font, fill=255)

                top = 22
                entries = [signal + "%", self.stats.interface, "", ""]
                for i, entry in enumerate(entries):
                    self.draw.text((i * offset + 4, top), entry, font=self.font, fill=255)            

            #
            # CASE BATTERY & MODEM STATE
            #

            if self.curr_show % 3 == 2:
                # # set stats headers
                top = 10
                offset = 4 * 8
                headers = ['BATTERY', '', 'MODEM', '']
                for i, header in enumerate(headers):
                    self.draw.text((i * offset + 4, top), header, font=self.font, fill=255)
                
                voltage = f'{bus_voltage:.2f}V {(current/1000):.2f}A'

                if charging:
                   voltage += " (*)" 
                else:
                   voltage += "    "
                
                top = 22
                entries = [voltage, "", modem_state, ""]
                for i, entry in enumerate(entries):
                    self.draw.text((i * offset + 4, top), entry, font=self.font, fill=255)            
            
            # Show and increment counter
            self.display.image(self.image)
            self.display.display()
            time.sleep(self.stats_interval)
            self.curr_show = (self.curr_show + 1) % 3

            # print("Current show:", self.curr_show)
            
    def enable_stats(self):
        # start stats display thread
        if not self.stats_enabled:
            self.stats_enabled = True
            self.stats_thread = threading.Thread(target=self._run_display_stats)
            self.stats_thread.start()
        
    def disable_stats(self):
        self.stats_enabled = False
        if self.stats_thread is not None:
            self.stats_thread.join()
        self.draw.rectangle((0, 0, self.image.width, self.image.height), outline=0, fill=0)
        self.display.image(self.image)
        self.display.display()

    def set_text(self, text):
        self.disable_stats()
        self.draw.rectangle((0, 0, self.image.width, self.image.height), outline=0, fill=0)
        
        lines = text.split('\n')
        top = 2
        for line in lines:
            self.draw.text((4, top), line, font=self.font, fill=255)
            top += 10
        
        self.display.image(self.image)
        self.display.display()
        

serverDisp = Display()
