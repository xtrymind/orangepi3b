from luma.oled.device import ssd1306
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw
import time
import psutil
import socket
import fcntl
import struct
import os # Import the os module for file operations

# --- Configuration ---
# Revise this to match your I2C bus if necessary (e.g., port=1 for /dev/i2c-1)
SERIAL_PORT = 2
I2C_ADDRESS = 0x3c # Default I2C address for 128x64 OLED

# Font settings
try:
    # Try a common monospaced font that might be available or installed
    FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    FONT_SIZE = 12
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
except IOError:
    # Fallback to default if the specific font is not found
    print(f"Warning: Font '{FONT_PATH}' not found. Using default font.")
    font = ImageFont.load_default()
    FONT_SIZE = 8 # Default font is smaller

# Update interval in seconds
UPDATE_INTERVAL = 2

# --- Helper Functions ---

def get_ip_address(ifname='end1'):
    """
    Get the IP address of a network interface.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15].encode('utf-8'))
        )[20:24])
    except IOError:
        return "N/A"

def get_stats():
    """
    Fetches system statistics.
    """
    cpu_percent = psutil.cpu_percent(interval=None) # Non-blocking
    mem_info = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/') # Root partition

    # --- MODIFIED RAM USAGE CALCULATION ---
    # Convert bytes to megabytes
    mem_total_mb = mem_info.total / (1024 * 1024)
    mem_used_mb = mem_info.used / (1024 * 1024)
    # mem_percent = mem_info.percent # We can still get this if needed, but display MB
    # --- END MODIFIED ---

    # --- MODIFIED: Read temperature from /etc/armbianmonitor/datasources/soctemp ---
    temp = "N/A"
    soctemp_path = "/etc/armbianmonitor/datasources/soctemp"
    if os.path.exists(soctemp_path):
        try:
            with open(soctemp_path, 'r') as f:
                raw_temp = f.read().strip()
                if raw_temp.isdigit():
                    # Value is in millidegrees Celsius, convert to Celsius
                    temp = f"{int(raw_temp) / 1000.0:.1f}°C"
                else:
                    temp = "Err" # Data not a number
        except Exception as e:
            temp = "ReadErr" # Error reading file
            print(f"Error reading soctemp: {e}")
    else:
        temp = "NoFile" # File not found
    # --- END MODIFIED ---

    ip_address = get_ip_address('end1') # Change 'eth0' to your Wi-Fi interface like 'wlan0' if using Wi-Fi
    if ip_address == "N/A":
        ip_address = get_ip_address('wlan0') # Try wlan0 if eth0 fails

    return {
        "cpu_percent": cpu_percent,
        "mem_percent": mem_info.percent,
        "mem_total_mb": mem_total_mb, # Added total RAM in MB
        "mem_used_mb": mem_used_mb,   # Added used RAM in MB
        "disk_percent": disk_usage.percent,
        "ip_address": ip_address,
        "temperature": temp
    }

# --- Main Logic ---

def main():
    print("Initializing OLED display...")
    try:
        serial = i2c(port=SERIAL_PORT, address=I2C_ADDRESS)
        device = ssd1306(serial)
        print("OLED display initialized successfully.")
    except Exception as e:
        print(f"Error initializing OLED: {e}")
        print("Please check your wiring, I2C address, and ensure I2C is enabled.")
        return

    print("Starting stats display loop. Press Ctrl+C to exit.")
    while True:
        stats = get_stats()

        with canvas(device) as draw:
            # Clear previous content (canvas context manager handles this)
            
            # Line 1: CPU Usage
            draw.text((0, 0), f"CPU: {stats['cpu_percent']:.1f}%", font=font, fill="white")
            
            # Line 2: RAM Usage
            #draw.text((0, FONT_SIZE + 2), f"RAM: {stats['mem_percent']:.1f}%", font=font, fill="white")
            
            # --- MODIFIED: RAM Usage in MB ---
            # Line 2: RAM Usage (Used/Total MB)
            draw.text((0, FONT_SIZE + 2), f"RAM: {stats['mem_used_mb']:.0f}/{stats['mem_total_mb']:.0f}MB", font=font, fill="white")
            # --- END MODIFIED ---
            

            # Line 3: Disk Usage
            #draw.text((0, (FONT_SIZE + 2) * 2), f"DSK: {stats['disk_percent']:.1f}%", font=font, fill="white")
            
            # Line 4: Temperature
            draw.text((0, (FONT_SIZE + 2) * 2), f"TMP: {stats['temperature']}", font=font, fill="white")

            # Line 5: IP Address
            # Adjust position based on FONT_SIZE and display height (64 pixels)
            # You might need to make font smaller or remove a line if it doesn't fit
            # For 128x64 display, 5 lines of 12pt font might be tight, especially with padding.
            # (FONT_SIZE + 2) * 4 should be around 56 pixels, leaving some space.
            draw.text((0, (FONT_SIZE + 2) * 3), f"IP: {stats['ip_address']}", font=font, fill="white")

        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting stats display.")
        # Optional: Clear the display on exit
        try:
            serial = i2c(port=SERIAL_PORT, address=I2C_ADDRESS)
            device = ssd1306(serial)
            device.clear()
        except Exception as e:
            print(f"Error clearing display on exit: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
