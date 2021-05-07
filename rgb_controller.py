#!/usr/bin/env python3

import pigpio
from time import sleep
import socket
import os
import pdb
import paho.mqtt.client as mqtt


client_id='hallwaylight1'
client_username = 'mqtt'
client_password = 'mqttmqtt'

effects = ['solid', 'strobe', 'pulse']

# topics

brightness_command_topic = f"/pistrip/{client_id}/brightness/command"
brightness_state_topic = f"/pistrip/{client_id}/brightness/state"

command_topic = f"/pistrip/{client_id}/command"
state_topic = f"/pistrip/{client_id}/state"
effect_command_topic = f"/pistrip/{client_id}/effect/command"
effect_state_topic = f"/pistrip/{client_id}/effect/state"

rgb_command_topic = f"/pistrip/{client_id}/rgb/command"
rgb_state_topic = f"/pistrip/{client_id}/rgb/state"


class RGB():
    RED_PIN = 27
    GREEN_PIN = 17
    BLUE_PIN = 22

    active_effect = 'color'

    def __init__(self, powered=False, start_color=[255,255,255], brightness=255):

        self.gpio = pigpio.pi()
        self.powered = powered
        self.current_state = start_color
        self.brightness = brightness

        if powered:
            self.power_on()
        else:
            self.power_off()

    def set_brightness(self, brightness):
        self.brightness = brightness
        self.show_color()

    def get_brightness(self):
        return self.brightness

    def get_color(self):
        r, g, b = self.current_state

        return f"{r},{g},{b}"

    def set_color(self, r, g, b):

        self.current_state=[r,g,b]
        self.show_color()

    def show_color(self, colors=None):
        if self.powered:
            brightness = self.brightness
            if colors:
                r, g, b = [int((brightness/256)*c) for c in colors]
            else:    
                r, g, b = [int((brightness/256)*c) for c in self.current_state]
            print(f"Effective color: {r},{g},{b}")

            self.gpio.set_PWM_dutycycle(self.RED_PIN, r)
            self.gpio.set_PWM_dutycycle(self.GREEN_PIN, g)
            self.gpio.set_PWM_dutycycle(self.BLUE_PIN, b)
        
        else:
            self.gpio.set_PWM_dutycycle(self.RED_PIN, 0)
            self.gpio.set_PWM_dutycycle(self.GREEN_PIN, 0)
            self.gpio.set_PWM_dutycycle(self.BLUE_PIN, 0)
        

    def power_on(self):
    
        self.powered = True
        self.show_color()

    def power_off(self):
  
        self.powered = False
        self.show_color()

    def pulse_off(self, t=0.1):

        r, g, b = self.current_state
        step = 50
        for i in range(step - 1, -1, -1):
            r1 = int(r * (i / step))
            g1 = int(g * (i / step))
            b1 = int(b * (i / step))
            
            self.show_color([r1, g1, b1])

    def pulse_on(self, t=0.1):

        r, g, b = self.current_state
        step = 50
        for i in range(1, step + 1):
            r1 = int(r * (i / step))
            g1 = int(g * (i / step))
            b1 = int(b * (i / step))
            
            self.show_color([r1, g1, b1])
            

    def flash(self, t=1):
        self.power_off()
        sleep(t)
        self.power_on()
        sleep(t)

    def pulse(self, speed=0):
        if speed==0:
            t = 0.1
        elif speed == 1:
            t = 0.05
        else:
            t = 0.025
        
        self.pulse_off(t=t)
        self.pulse_on(t=t)


def on_message(client, userdata, message):
    
    topic = message.topic

    if topic == brightness_command_topic:
        print("Brightness called")
        rgb.set_brightness(int(message.payload.decode()))
        # pdb.set_trace()
    elif topic == command_topic:
        if message.payload == b'power_on':
            print("Power on called")
            rgb.power_on()
        elif message.payload == b'power_off':
            print("Power off called")
            rgb.power_off()
    elif topic == rgb_command_topic:
        r, g, b = [int(c) for c in message.payload.decode().split(',')]

        rgb.set_color(r, g, b)
    elif topic == effect_command_topic:
        cmd = message.payload.decode()
        if cmd == 'flash':
            rgb.active_effect = 'flash'
        elif cmd == 'pulse':

            rgb.active_effect = 'pulse'
        elif cmd == 'none' or cmd == 'solid':
            rgb.active_effect = 'color'

    # pdb.set_trace()

rgb = RGB(powered=True)

if __name__ == "__main__":

    



    client = mqtt.Client(client_id = client_id)
    # client.on_connect = on_connect
    # client.on_message = on_message
    client.username_pw_set(username=client_username, password=client_password)
    client.on_message = on_message
    client.connect("192.168.1.211", 1883, 60)

    client.subscribe(brightness_command_topic)
    client.subscribe(command_topic)
    client.subscribe(effect_command_topic)
    client.subscribe(rgb_command_topic)
    
    while True:

        client.loop_start()
        print("looping")
        if rgb.active_effect == 'flash':
            rgb.flash()
        elif rgb.active_effect == 'pulse':
            rgb.pulse()
        else:
            sleep(1)
        client.loop_stop()

