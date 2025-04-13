import time
from PIL import Image, ImageDraw

# Attempt to import Raspberry Pi-specific libraries
try:
    import RPi.GPIO as GPIO
    import spidev
    from st7789 import ST7789
    HAS_LCD = True
except ImportError:
    print("ERROR: Crucial libraries (RPi.GPIO, spidev, ST7789) not found.")
    print("Please ensure they are installed: sudo pip3 install RPi.GPIO spidev st7789")
    HAS_LCD = False
    exit()

print("Libraries imported.")

lcd = None
try:
    # --- Configuration for Waveshare 2-inch LCD (ST7789) ---
    # IMPORTANT: Verify these pins against the Waveshare example code (2inch_LCD_test.py)
    #            Waveshare Docs: RST=27, DC=25, BL=18, CS=SPI0 CE0 (GPIO 8), Port=0
    lcd = ST7789(
        port=0,             # SPI Port (usually 0)
        cs=0,               # SPI Chip Select (0 or 1, corresponds to CE0 or CE1 / GPIO 8 or 7)
        dc=25,              # Data/Command (GPIO 25 - Corrected)
        rst=27,             # Reset (GPIO 27 - Corrected)
        backlight=18,       # Backlight (GPIO 18 - Corrected) (Set to None if no backlight control)
        width=320,          # --- Display Width for 2" Screen ---
        height=240,         # --- Display Height for 2" Screen ---
        rotation=0,         # --- Adjust rotation: 0, 90, 180 --- (Try 0 first)
        spi_speed_hz=10000000 # SPI Speed (Lowered from 40MHz to 10MHz for stability test)
    )
    # -----------------------------------------------------------
    print("ST7789 object created.")
    lcd.begin()
    print("ST7789 LCD Initialized Successfully (320x240).")

    # Create a simple blue image
    print("Creating a blue test image...")
    image = Image.new("RGB", (lcd.width, lcd.height), "BLUE")
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "Hello LCD! (BLUE?)", fill="WHITE")
    print("Test image created.")

    # Display the image
    print("Attempting to display image on LCD...")
    lcd.display(image)
    print("Image displayed! Check the LCD screen.")

    # Keep the image displayed for a few seconds
    time.sleep(10)
    print("Test complete.")

except Exception as e:
    print(f"An error occurred: {e}")
    # Attempt to clean up GPIO if possible, even on error
    # Be cautious with GPIO cleanup if other scripts might use it.
    # try:
    #     GPIO.cleanup()
    # except NameError:
    #     pass # GPIO might not have been imported/initialized
    # except RuntimeError as re:
    #     print(f"Ignoring GPIO cleanup error: {re}")

finally:
    # Optional: You might want to explicitly turn off backlight or clear screen here
    # if lcd and HAS_LCD:
    #     try:
    #         # lcd.set_backlight(False) # Requires st7789 library support for backlight control
    #         pass
    #     except Exception as e:
    #         print(f"Error during final cleanup: {e}")
    print("Exiting test script.") 