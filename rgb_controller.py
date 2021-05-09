#!/usr/bin/env python3

import pigpio
from time import sleep

import os
import pdb
import paho.mqtt.client as mqtt
import asyncio
import json
import random

state_file = '/opt/mqtt_rgb/state.json'
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

    def __init__(self, powered=False, start_color=[255,255,255], brightness=255):

        self.gpio = pigpio.pi()
        
        if not self.read_state():
            self.powered = powered
            self.current_state = start_color
            self.brightness = brightness
            self.active_effect = 'color'
        if self.powered:
            self.power_on()
        else:
            self.power_off()
    
    def read_state(self):
        try:
            if os.path.exists(state_file):
                current_state = json.loads(open(state_file).read())

                self.active_effect = current_state['active_effect']
                self.powered = current_state['powered']
                self.current_state = current_state['current_state']
                self.brightness = current_state['brightness']
                return True
        except:
            pass
        return False


    def save_state(self):
        current_state = {'active_effect': self.active_effect,
                         'powered': self.powered,
                         'current_state': self.current_state,
                         'brightness': self.brightness}
        
        open(state_file, 'w').write(json.dumps(current_state))

    def set_brightness(self, brightness):
        self.brightness = brightness
        self.show_color()
        self.save_state()

    def get_brightness(self):
        return self.brightness

    def get_color(self):
        r, g, b = self.current_state

        return f"{r},{g},{b}"

    def set_color(self, r, g, b):

        self.current_state=[r,g,b]
        self.show_color()
        self.save_state()

    def show_color(self, colors=None):
        if self.powered:
            brightness = self.brightness
            if colors:
                r, g, b = [int((brightness/256)*c) for c in colors]
            else:    
                r, g, b = [int((brightness/256)*c) for c in self.current_state]
            # print(f"Effective color: {r},{g},{b}")

            self.gpio.set_PWM_dutycycle(self.RED_PIN, r)
            self.gpio.set_PWM_dutycycle(self.GREEN_PIN, g)
            self.gpio.set_PWM_dutycycle(self.BLUE_PIN, b)
        
        else:
            self.gpio.set_PWM_dutycycle(self.RED_PIN, 0)
            self.gpio.set_PWM_dutycycle(self.GREEN_PIN, 0)
            self.gpio.set_PWM_dutycycle(self.BLUE_PIN, 0)
        

    def set_effect(self, effect):
        self.active_effect = effect
        self.save_state()

    def power_on(self):
    
        self.powered = True
        self.show_color()
        self.save_state()

    def power_off(self):
  
        self.powered = False
        self.show_color()
        self.save_state()

    def go_to_color(self, end_rgb=None, step=100):

        
        r, g, b = self.current_state
        # print(f"Start: {r} {g} {b}")
        if end_rgb:
            r1, g1, b1 = end_rgb  
        else:
            r1, g1, b1 = [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]
        for s in range(step):
            sleep(.01)
            r2 = r + int(((r1 - r) / step)*s)
            g2 = g + int(((g1 - g) / step)*s)
            b2 = b + int(((b1 - b) / step)*s)
            
            # print(f"Change: {r2} {g2} {b2}")    
            self.show_color([r2, g2, b2])

        self.set_color(r1, g1, b1)
        # print(f"End: {r1} {g1} {b1}")

    def pulse_off(self, step=100):

        r, g, b = self.current_state
        
        for i in range(step - 1, -1, -1):
            r1 = int(r * (i / step))
            g1 = int(g * (i / step))
            b1 = int(b * (i / step))
            
            self.show_color([r1, g1, b1])

    def pulse_on(self, step=100):

        r, g, b = self.current_state
        
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

    def pulse(self, step=100):
        
        
        self.pulse_off(step=step)
        self.pulse_on(step=step)


def on_message(client, userdata, message):
    
    topic = message.topic
    # print(topic)
    if topic == brightness_command_topic:
        print("Brightness called")
        rgb.set_brightness(int(message.payload.decode()))
        client.publish(brightness_state_topic, message.payload)
        # pdb.set_trace()
    elif topic == command_topic:
        if message.payload == b'ON':
            print("Power on called")
            rgb.power_on()
            
        elif message.payload == b'OFF':
            print("Power off called")
            rgb.power_off()
        client.publish(state_topic, message.payload)
        
    elif topic == rgb_command_topic:
        
        r, g, b = [int(c) for c in message.payload.decode().split(',')]
        print(f"Changing color to {r}-{g}-{b}")
        try:
            rgb.set_color(r, g, b)
        except Exception as e:
            print(e)
        client.publish(rgb_state_topic, ",".join([r, g, b].encode()))

    elif topic == effect_command_topic:
        cmd = message.payload.decode()
        
        

        
        if cmd == 'none' or cmd == 'solid':
            rgb.set_effect('color')
        else:
            rgb.set_effect(cmd)
        client.publish(effect_state_topic, message.payload)
    
    # pdb.set_trace()



async def monitor_mqtt(rgb):
    client = mqtt.Client(client_id = client_id)
    
    client.username_pw_set(username=client_username, password=client_password)
    client.on_message = on_message
    client.connect("192.168.1.211", 1883, 60)

    client.publish(effect_state_topic, b'none')
    client.publish(state_topic, b'ON')
    client.publish(rgb_state_topic, b'255,255,255')
    client.publish(brightness_state_topic, b'255')
    
    client.subscribe(brightness_command_topic)
    client.subscribe(command_topic)
    client.subscribe(effect_command_topic)
    client.subscribe(rgb_command_topic)
    
    client.loop_start()
    await asyncio.sleep(5)
    client.loop_stop()

async def control_lights(rgb):
    while True:
        # print(rgb.active_effect)
        if rgb.active_effect == 'flash':
            rgb.flash()
        elif rgb.active_effect == 'fast_flash':
            rgb.flash(t=.5)
        elif rgb.active_effect == 'slow_flash':
            rgb.flash(t=2)
        elif rgb.active_effect == 'pulse':
            rgb.pulse()
        elif rgb.active_effect == 'fast_pulse':
            rgb.pulse(step=50)
        elif rgb.active_effect == 'slow_pulse':
            rgb.pulse(step=150)
        elif rgb.active_effect == "random_fade":
            rgb.go_to_color(step=200)


        else:
            sleep(1)
rgb = RGB(powered=True)    
async def main_loop():
    

    loop = asyncio.get_event_loop()

    loop.create_task(monitor_mqtt(rgb))
    loop.create_task(control_lights(rgb))

    loop.run_forever()

    
if __name__ == "__main__":

    asyncio.run(main_loop())



    
    
    
