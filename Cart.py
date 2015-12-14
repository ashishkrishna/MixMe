# MixMe: EE 249 Final Project
#
# Cart.py 11/30/2015
#		Access sensor data and control the motors on the MixMe drink cart.
#
# Usage:
	# 1) Add the line "import Cart" to access module
	# 2) Use Cart.setup() to configure GPIO pins for encoder and motors
	# 3) Use Cart.runMotor(speed) to control motors. 
	#	 The speed parameter determines the speed of the cart as a fraction of max speed (speed = 50 means 50% of max speed)
	#	 Negative speed values will run the motors backwards
	# 4) Use Cart.readPressure() to read data from pressure sensor
	# 5) To get current encoder count read the global variable Cart.count
########################################################################################

#Imports
from __future__ import division
import RPi.GPIO as GPIO
import spidev
import numpy
import time

#Constants


#Global variables


class Cart:

        def __init__(self, encoderPin, motorPin1, motorPin2, idlePin, pos, bumpsensor, system):
                encoder_transform = 1/184
                #Global variable initialization
                self.rotation = 1
                self.idleCount = pos/encoder_transform
                self.count = self.idleCount
                self.reply = [0 for i in range(20)]
                self.cmd = 128
                self.drink = None
                self.lvl = 0
                self.system = system
                self.is_pouring = False
                self.MAX_PWM = 45
                # GPIO setup
                GPIO.setmode(GPIO.BOARD)

                # Motor setup
                GPIO.setup(motorPin1,GPIO.OUT)
                GPIO.setup(motorPin2,GPIO.OUT)
                self.p1 = GPIO.PWM(motorPin1, 10000)
                self.p2 = GPIO.PWM(motorPin2, 10000)
                self.p1.start(0)
                self.p2.start(0)
                self.speed = 0
                self.idle_pos = pos
                self.curr_pos = pos
                self.move_dir = None
                self.bump_sensor = bumpsensor
                self.idlePin = idlePin
                if(self.bump_sensor == 1):
                        GPIO.setup(36, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                        GPIO.add_event_detect(36, GPIO.FALLING, callback = system.bump)

                # Encoder setup
                GPIO.setup(encoderPin,GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(encoderPin, GPIO.RISING, callback=self.counter)
                GPIO.setup(idlePin, GPIO.IN)
                # Pressure sensor setup
                self.conn = spidev.SpiDev()
                self.conn.open(0, 0)
                self.conn.max_speed_hz = 1200000 # 1.2 MHz
                self.valve = None
                self.drink = None


        #Encoder callback function
        def counter(self, encoderPin):
            if True:
                if self.rotation == 1:
                        self.count = self.count + 1
                else:
                        self.count = self.count - 1
                #print("count = " + str(self.count))
            # elif self.idle_pos !=0:
            #     if self.rotation == 1:
            #             self.count = self.count - 1
            #     else:
            #             self.count = self.count + 1
            #     print("count = " + str(self.count))


        #Checking for orders
        def check_for_orders(self, queue1, system):
            #print("CHECKING FOR ORDERS")
            if self.lvl == 0:
                    if(queue1.length == 0):
                        return False
                    else:
                        self.drink = queue1.dequeue(system)
                        if(self.idle_pos != 0):
                            temp1 = self.drink.liq1
                            temp2 = self.drink.liq2
                            temp3 = self.drink.liq3
                            temp4 = self.drink.liq4
                            self.drink.liq4 = temp1
                            self.drink.liq3 = temp2
                            self.drink.liq2 = temp3
                            self.drink.liq1 = temp4
                        if self.drink != None:
                            self.lvl = 1
                            return True
                        else:
                            return False
            else:
                return True

            


        #Motor control
        def runMotor(self, speed):
                if speed > self.MAX_PWM:
                        speed = self.MAX_PWM

                elif speed < -self.MAX_PWM:
                        speed = -self.MAX_PWM

                if speed > 0:
                        self.rotation = 1
                        self.p1.ChangeDutyCycle(speed)		
                        self.p2.ChangeDutyCycle(0)
                else:
                
                        self.rotation = 0
                        self.p1.ChangeDutyCycle(0)
                        self.p2.ChangeDutyCycle(-speed)

        def bitstring(self, n):
                s = bin(n)[2:]
                return '0'*(8-len(s)) + s

                #Pressure sensor read input
        def readPressure(self, adc_channel=0, spi_channel=0):
                global cmd
                global conn
                global reply

                for i in range(0,20):
                        if adc_channel:
                            self.cmd += 32
                        reply_bytes = self.conn.xfer2([cmd, 0])
                        reply_bitstring = ''.join(bitstring(n) for n in reply_bytes)
                        self.reply[i] = int(reply_bitstring[5:15],2) / 2**10
                        time.sleep(.01)
                return numpy.mean(self.reply)


        #TODO: Proceed to the valve
        def proceed_to_valve(self, valve):
            system = self.system
            encoder_transform = 1/184
            dist = abs(valve.rh_distance-self.idle_pos)
            #Assuming max_speed is 1 rev/second
            if(valve.rh_distance - self.idle_pos < 0 or valve.rh_distance - self.idle_pos > 0):
                #self.move_dir = left
                while(abs(valve.rh_distance-self.curr_pos) > 0):
                    #print(str(valve.rh_distance - self.curr_pos))
                    self.runMotor(2*(valve.rh_distance-self.curr_pos))
                    self.curr_pos = self.count*encoder_transform
                    #print(str(self.curr_pos))
                    #print(str(self.count))
                    if(self.bump_sensor == 0 and system.bump_compliment == 1):
                        self.runMotor(0)
                        #print("Check A")
                        time.sleep(3)
                        system.deadlock_handler(self)
                        system.complimentary_lock.acquire()
                        system.bump_compliment = 0
                        system.complimentary_lock.release()
                        
                    #self.curr_pos = self.curr_pos - (time.time()-start)*self.speed
                    if(self.bump_sensor == 1 and system.bump_primary == 1):
                        self.runMotor(0)
                        #print("Check B")
                        time.sleep(3)
                        system.deadlock_handler(self)
                        system.primary_lock.acquire()
                        system.bump_primary = 0
                        system.primary_lock.release()
                print(str(self.count))        
                self.runMotor(0)
                time.sleep(2)
                return

                
            
                
                    
                    
    
    




        #TODO: Return from valve to idle position
        def return_to_idle(self):
            #print("Going to idle")
            # system = self.system
            # encoder_transform = 1/184
            # dist = abs(self.curr_pos-self.idle_pos)
            # while(abs(self.curr_pos-self.idle_pos) > 0):
            #     self.runMotor(2*(self.idle_pos-self.curr_pos))
            #     self.curr_pos = self.count*encoder_transform

            # time.sleep(2)
            # self.runMotor(0)
            while not GPIO.input(self.idlePin):
                if self.idle_pos == 0:
                    self.runMotor(-75)
                else:
                    self.runMotor(75)
            self.runMotor(0)
            self.count = self.idleCount
            return
           

 
        def cleanup(self):
                global conn
                global p1
                global p2
                p1.stop()
                p2.stop()
                conn.close()
                GPIO.cleanup()
