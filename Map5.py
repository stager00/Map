from picrawler import Picrawler
from robot_hat import TTS, Music
from robot_hat import Ultrasonic, Pin
import time
import cv2
import readchar
import Adafruit_SSD1306
from PIL import Image, ImageDraw, ImageFont
import subprocess
from vilib import Vilib

# Initialize OLED display
RST = None
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)
disp.begin()
disp.clear()
disp.display()

# Create blank image for drawing.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

tts = TTS()
music = Music()

crawler = Picrawler() 
sonar = Ultrasonic(Pin("D2"), Pin("D3"))
music.music_set_volume(100)

alert_distance = 15  # Distance threshold for detecting obstacles
cliff_threshold = 50  # Distance threshold for detecting cliffs
view_block_threshold = 0.5  # Threshold for deciding if the view is blocked (50% of the view)
speed = 80  # Default speed

manual = '''
Press keys on keyboard to control PiCrawler!
    W: Forward
    A: Turn left
    S: Backward
    D: Turn right
    0: Switch to obstacle avoidance mode
    1: Toggle obstacle detection
    2: Double height and step height
    3: Speed 70%
    4: Speed 100%
    5: Speed 150%
    6: Toggle gait (Wave/Ripple/Diagonal)
    C: Toggle camera feed
    U: Look up
    J: Look down
    F1: Toggle avoid.py
    F2: Toggle bull_fight.py
    F3: Toggle twist.py
    F4: Toggle treasure_hunt.py
    7: Toggle cliff detection

    Ctrl^C: Quit
'''

gait = "wave"  # Default gait
external_process = None
cliff_detection_enabled = True

def show_info():
    print("\033[H\033[J", end='')  # clear terminal window
    print(manual)
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((0, 0), f"Gait: {gait}", font=font, fill=255)
    disp.image(image)
    disp.display()

def get_ultrasonic_distance():
    distance = sonar.read()
    return distance

def is_view_blocked():
    Vilib.camera_start()
    Vilib.display()
    Vilib.color_detect("red") 
    if Vilib.detect_obj_parameter['color_n'] != 0:
        coordinate_x = Vilib.detect_obj_parameter['color_x']
        if coordinate_x < 100 or coordinate_x > 220:
            return True
    return False

def high_step():
    if gait == "wave":
        steps = [
            [[70, 10, -10], [60, 0, -20], [60, 0, -20], [60, 0, -20]],  # Move leg 1 with higher step
            [[60, 0, -20], [50, -10, -30], [60, 0, -20], [60, 0, -20]],  # Move leg 2 with higher step
            [[60, 0, -20], [60, 0, -20], [70, 10, -10], [60, 0, -20]],  # Move leg 3 with higher step
            [[60, 0, -20], [60, 0, -20], [60, 0, -20], [50, -10, -30]],  # Move leg 4 with higher step
            [[60, 0, -20], [60, 0, -20], [60, 0, -20], [60, 0, -20]]   # Back to initial position with higher step
        ]
    elif gait == "ripple":
        steps = [
            [[70, 10, -20], [60, 0, -30], [60, 0, -30], [60, 0, -30]],  # Move leg 1
            [[60, 0, -30], [70, 10, -20], [60, 0, -30], [60, 0, -30]],  # Move leg 2
            [[60, 0, -30], [60, 0, -30], [70, 10, -20], [60, 0, -30]],  # Move leg 3
            [[60, 0, -30], [60, 0, -30], [60, 0, -30], [70, 10, -20]],  # Move leg 4
            [[60, 0, -30], [60, 0, -30], [60, 0, -30], [60, 0, -30]]   # Back to initial position
        ]
    elif gait == "diagonal":
        steps = [
            [[70, 10, -20], [60, 0, -30], [70, 10, -20], [60, 0, -30]],  # Move legs 1 and 3
            [[60, 0, -30], [50, -10, -40], [60, 0, -30], [50, -10, -40]],  # Move legs 2 and 4
            [[60, 0, -30], [60, 0, -30], [60, 0, -30], [60, 0, -30]]   # Back to initial position
        ]
    for step in steps:
        crawler.do_step(step, speed=speed)

def normal_step():
    if gait == "wave":
        steps = [
            [[70, 10, -20], [60, 0, -30], [60, 0, -30], [60, 0, -30]],  # Move leg 1
            [[60, 0, -30], [50, -10, -40], [60, 0, -30], [60, 0, -30]],  # Move leg 2
            [[60, 0, -30], [60, 0, -30], [70, 10, -20], [60, 0, -30]],  # Move leg 3
            [[60, 0, -30], [60, 0, -30], [60, 0, -30], [50, -10, -40]],  # Move leg 4
            [[60, 0, -30], [60, 0, -30], [60, 0, -30], [60, 0, -30]]   # Back to initial position
        ]
    elif gait == "ripple":
        steps = [
            [[70, 10, -20], [60, 0, -30], [60, 0, -30], [60, 0, -30]],  # Move leg 1
            [[60, 0, -30], [70, 10, -20], [60, 0, -30], [60, 0, -30]],  # Move leg 2
            [[60, 0, -30], [60, 0, -30], [70, 10, -20], [60, 0, -30]],  # Move leg 3
            [[60, 0, -30], [60, 0, -30], [60, 0, -30], [70, 10, -20]],  # Move leg 4
            [[60, 0, -30], [60, 0, -30], [60, 0, -30], [60, 0, -30]]   # Back to initial position
        ]
    elif gait == "diagonal":
        steps = [
            [[70, 10, -20], [60, 0, -30], [70, 10, -20], [60, 0, -30]],  # Move legs 1 and 3
            [[60, 0, -30], [50, -10, -40], [60, 0, -30], [50, -10, -40]],  # Move legs 2 and 4
            [[60, 0, -30], [60, 0, -30], [60, 0, -30], [60, 0, -30]]   # Back to initial position
        ]
    for step in steps:
        crawler.do_step(step, speed=speed)
def double_height_step():
    # Define double height and step coordinates
    steps = [
        [[70, 10, -80], [60, 0, -100], [60, 0, -100], [60, 0, -100]],  # Move leg 1 with double step height
        [[60, 0, -100], [70, 10, -80], [60, 0, -100], [60, 0, -100]],  # Move leg 2 with double step height
        [[60, 0, -100], [60, 0, -100], [70, 10, -80], [60, 0, -100]],  # Move leg 3 with double step height
        [[60, 0, -100], [60, 0, -100], [60, 0, -100], [70, 10, -80]],  # Move leg 4 with double step height
        [[60, 0, -100], [60, 0, -100], [60, 0, -100], [60, 0, -100]]   # Back to initial position with double height
    ]
    for step in steps:
        print(f"Executing step: {step}")  # Debugging print statement
        crawler.do_step(step, speed=speed)

def look_up():
    # Define coordinates to look up (raise front, lower rear)
    steps = [
        [[60, 0, -10], [60, 0, -10], [60, 0, -30], [60, 0, -30]],  # Raise front legs
        [[60, 0, -10], [60, 0, -10], [60, 0, -30], [60, 0, -30]]   # Maintain position
    ]
    for step in steps:
        crawler.do_step(step, speed=speed)

def look_down():
    # Define coordinates to look down (lower front, raise rear)
    steps = [
        [[60, 0, -30], [60, 0, -30], [60, 0, -10], [60, 0, -10]],  # Lower front legs
        [[60, 0, -30], [60, 0, -30], [60, 0, -10], [60, 0, -10]]   # Maintain position
    ]
    for step in steps:
        crawler.do_step(step, speed=speed)

def is_cliff_detected():
    if not cliff_detection_enabled:
        return False

    # Check distance using ultrasonic sensor
    distance = get_ultrasonic_distance()
    print(f"Ultrasonic Distance: {distance} cm")  # Debugging print statement
    if distance > cliff_threshold:
        print("Ultrasonic sensor detected a cliff")
        return True

    # Check for edges using the camera
    Vilib.camera_start()
    Vilib.display()
    Vilib.color_detect("red") 
    if Vilib.detect_obj_parameter['color_n'] != 0:
        coordinate_x = Vilib.detect_obj_parameter['color_x']
        if coordinate_x < 100 or coordinate_x > 220:
            print("Camera detected a cliff")
            return True

    return False

def obstacle_avoidance_mode():
    if is_cliff_detected():
        print("Cliff detected! Stopping to confirm.")
        high_step()  # Raise to high stance
        look_down()  # Look down to confirm cliff
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((0, 0), "Danger: Cliff detected!", font=font, fill=255)
        disp.image(image)
        disp.display()
        time.sleep(1)  # Pause to allow for confirmation
        crawler.do_action('backward', 2, speed)  # Back up
        crawler.do_action('turn right', 3, speed)  # Turn around
        print("Turning around to avoid cliff")
        time.sleep(1)  # Pause to complete the turn
        return

    distance = get_ultrasonic_distance()
    print(f"Distance: {distance} cm")
    
    # Display distance on OLED
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((0, 0), f"Distance: {distance} cm", font=font, fill=255)
    if distance <= alert_distance:
        draw.text((0, 20), "Obstacle detected!", font=font, fill=255)
    disp.image(image)
    disp.display()
    
    if distance < 0:
        pass
    elif distance <= alert_distance:
        if is_view_blocked():
            try:
                music.sound_play_threading('./sounds/sign.wav', volume=100)
            except Exception as e:
                print(e)
            print("Turning left to avoid the obstacle")
            crawler.do_action('turn left angle', 3, speed)
            time.sleep(0.2)
        else:
            print("Stepping over the obstacle")
            high_step()  # Call the high step function
    else:
        print("Path clear. Normal walking.")
        normal_step()  # Return to normal walking
        crawler.do_action('forward', 1, speed)
        time.sleep(0.2)

def toggle_external_script(script_name):
    global external_process
    if external_process and external_process.poll() is None:
        external_process.terminate()
        external_process = None
        print(f"{script_name} stopped")
    else:
        external_process = subprocess.Popen(["python3", f"./examples/{script_name}"])
        print(f"{script_name} started")

def main():
    global speed, gait, cliff_detection_enabled  # Add this line to declare 'speed', 'gait', and 'cliff_detection_enabled' as global
    show_info()
    mode = "manual"
    obstacle_detection_enabled = False
    double_height_enabled = False
    camera_feed_enabled = False
    gait = "wave"  # Default gait
    
    while True:
        if mode == "manual":
            key = readchar.readkey()
            key = key.lower()
            if key in ('wsad'):
                if 'w' == key:
                    if obstacle_detection_enabled:
                        distance = get_ultrasonic_distance()
                        if distance > 0 and distance <= alert_distance:
                            if is_view_blocked():
                                print("Obstacle detected, attempting to step over")
                                high_step()
                            else:
                                if double_height_enabled:
                                    double_height_step()
                                else:
                                    normal_step()
                        else:
                            if double_height_enabled:
                                double_height_step()
                            else:
                                normal_step()
                    else:
                        if double_height_enabled:
                            double_height_step()
                        else:
                            normal_step()
                elif 's' == key:
                    crawler.do_action('backward', 1, speed)          
                elif 'a' == key:
                    crawler.do_action('turn left', 1, speed)           
                elif 'd' == key:
                    crawler.do_action('turn right', 1, speed)
                time.sleep(0.05)
                show_info()
            elif key == '0':
                print("Switching to obstacle avoidance mode")
                mode = "obstacle_avoidance"
            elif key == '1':
                obstacle_detection_enabled = not obstacle_detection_enabled
                print(f"Obstacle detection {'enabled' if obstacle_detection_enabled else 'disabled'}")
                if not obstacle_detection_enabled and double_height_enabled:
                    print("Returning to standard stance")
                    normal_step()
                    double_height_enabled = False
            elif key == '2':
                double_height_enabled = not double_height_enabled
                if double_height_enabled:
                    print("Double height and step height enabled")
                    double_height_step()
                else:
                    print("Double height and step height disabled")
                    normal_step()
            elif key == '3':
                speed = 70
                print("Speed set to 70%")
            elif key == '4':
                speed = 100
                print("Speed set to 100%")
            elif key == '5':
                speed = 150
                print("Speed set to 150%")
            elif key == '6':
                print("Key 6 pressed")  # Debugging print statement
                print(f"Current gait before update: {gait}")  # Debugging print statement
                if gait == "wave":
                    gait = "ripple"
                elif gait == "ripple":
                    gait = "diagonal"
                else:
                    gait = "wave"
                print(f"Gait set to {gait}")  # Debugging print statement
                show_info()
            elif key == 'c':
                camera_feed_enabled = not camera_feed_enabled
                if camera_feed_enabled:
                    print("Camera feed enabled")
                    Vilib.camera_start()
                    Vilib.display()
                    while camera_feed_enabled:
                        if Vilib.detect_obj_parameter['color_n'] != 0:
                            coordinate_x = Vilib.detect_obj_parameter['color_x']
                            if coordinate_x < 100:
                                crawler.do_action('turn left', 1, speed)
                            elif coordinate_x > 220:
                                crawler.do_action('turn right', 1, speed)
                            else:
                                crawler.do_action('forward', 2, speed)
                        if cv2.waitKey(1) & 0xFF == ord('c'):
                            camera_feed_enabled = False
                            Vilib.camera_close()
                            print("Camera feed disabled")
                            break
            elif key == 'u':
                print("Looking up")
                look_up()
            elif key == 'j':
                print("Looking down")
                look_down()
            elif key == '\x1b':  # ESC key
                break
            elif key == '\x03':  # Ctrl+C
                break
            elif key == '\x1bOP':  # F1 key
                toggle_external_script('avoid.py')
            elif key == '\x1bOQ':  # F2 key
                toggle_external_script('bull_fight.py')
            elif key == '\x1bOR':  # F3 key
                toggle_external_script('twist.py')
            elif key == '\x1bOS':  # F4 key
                toggle_external_script('treasure_hunt.py')
            elif key == '7':
                cliff_detection_enabled = not cliff_detection_enabled
                print(f"Cliff detection {'enabled' if cliff_detection_enabled else 'disabled'}")
            show_info()
        elif mode == "obstacle_avoidance":
            obstacle_avoidance_mode()
            time.sleep(0.1)

if __name__ == "__main__":
    main()
