import time
from PIL import Image, ImageDraw

# Attempt to import Raspberry Pi-specific libraries
try:
    import RPi.GPIO as GPIO
    import spidev
    from ST7789 import ST7789
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
    #            Common pins: RST=25, DC=9, BL=13, CS=SPI0 CS0 (GPIO 8), Port=0
    lcd = ST7789(
        port=0,             # SPI Port (usually 0)
        cs=0,               # SPI Chip Select (0 or 1, corresponds to CE0 or CE1 / GPIO 8 or 7)
        dc=9,               # Data/Command (GPIO 9)
        rst=25,             # Reset (GPIO 25)
        backlight=13,       # Backlight (GPIO 13) (Set to None if no backlight control)
        width=320,          # --- Display Width for 2" Screen ---
        height=240,         # --- Display Height for 2" Screen ---
        rotation=270,       # --- Adjust rotation: 0/90/180/270 (270 often needed for landscape) ---
        spi_speed_hz=40000000 # SPI Speed (can try adjusting if issues)
    )
    # -----------------------------------------------------------
    print("ST7789 object created.")
    lcd.begin()
    print("ST7789 LCD Initialized Successfully (320x240).")

    # Create a simple red image
    print("Creating a red test image...")
    image = Image.new("RGB", (lcd.width, lcd.height), "RED")
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "Hello LCD!", fill="WHITE")
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