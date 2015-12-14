import threading
import Cart
import time
from pubnub import Pubnub
import math
import RPi.GPIO as GPIO
global Orderqueue, System



#A generic Queue class, allows resizing 
class Queue:
       def __init__(self, queuelength):
           self.quelim = queuelength
           self.length = 0
           self.queue = []
           self.lock = threading.Lock()
           return

       def enqueue(self, drink):
           if(self.length >= self.quelim):
               return
           self.lock.acquire()
           self.queue.append(drink)
           print("Added drink to queue")
           self.length = self.length+1
           self.lock.release()
           return
        
       def dequeue(self, system):
           self.lock.acquire()
           if(self.length == 0):
              self.lock.release()
              return
           drink_next = self.queue.pop()
           self.length = self.length - 1
           if (drink_next == None):
               self.lock.release()
               return 
           drink_next.priority = time.time()
           system.set_priority_func(drink_next)
           self.lock.release()
           return drink_next


#System's highest priority drink used in deadlock scenarios 
class System:
       def __init__(self):
              self.general_lock = threading.Lock()
              self.deadlock_locking = threading.Lock()
              self.highest_priority_drink  = 0
              self.deadlock_flag = 0
              self.drinks = []
              self.carts = []
              self.complimentary_lock = threading.Lock()
              self.primary_lock = threading.Lock()
              self.bump_compliment = 0
              self.bump_primary = 0

       def bump(self, channel=36):
              #print("!!!!!!!!!!!!!!!!BUMP!!!!!!!!!!!!!!!!!!!")
              self.primary_lock.acquire()
              self.complimentary_lock.acquire()
              self.bump_primary = 1
              self.bump_compliment = 1
              self.complimentary_lock.release()
              self.primary_lock.release()
              return

       def delete_drink(self, drink):
              self.general_lock.acquire()
              count = 0
              while(count < len(self.drinks)):
                     if(self.drinks[count].priority == drink.priority):
                            del[self.drinks[count]]
                     count = count+1
              if(len(self.drinks)> 0):
                newmax = self.drinks[0]
              count2 = 0
              while(count2 < len(self.drinks)):
                     if(self.drinks[count2].priority < newmax.priority):
                            newmax = self.drinks[count2]
                     count2 = count2+1
              if(len(self.drinks) >0):
                self.highest_priority_drink = newmax
              else:
                self.highest_priority_drink = 0
              self.general_lock.release()
              return
                     
       def set_priority_func(self, drink):
              self.general_lock.acquire()
              if (self.highest_priority_drink == 0):
                     self.highest_priority_drink = drink
                     self.general_lock.release()
                     return
              if (drink.priority < self.highest_priority_drink.priority):
                     self.highest_priority_drink = drink
              self.general_lock.release()
              return

       def set_deadlock_flag(self, arg):
              #self.deadlock_locking.acquire()
              self.deadlock_flag = arg
              #self.deadlock_locking.release()
              return
              
       def deadlock_handler(self, cart_arg):
            print("IN THE DEADLOCK HANDLER")
            if(self.carts[0].is_pouring or self.carts[1].is_pouring):
              if(self.carts[0] is cart_arg):
                if(self.carts[0].is_pouring):
                  return
                if(self.carts[1].is_pouring):
                  while(self.carts[1].is_pouring):
                    continue
                  time.sleep(2)
                  return
              if(self.carts[1] is cart_arg):
                if(self.carts[1].is_pouring):
                  return
                if(self.carts[0].is_pouring):
                 while(self.carts[0].is_pouring):
                    continue
                 time.sleep(2)
                 return
            self.set_deadlock_flag(1)
            if(cart_arg.drink.priority > self.highest_priority_drink.priority):
                saved_valve = cart_arg.valve
                cart_arg.valve.release()
                cart_arg.valve = None
                cart_arg.return_to_idle()
                while(self.deadlock_flag == 1):
                  continue
                    #cart_arg.runMotor(0)
                    #print("In LOOP")
                cart_arg.valve = saved_valve.add()
                return
            if(cart_arg.drink.priority == self.highest_priority_drink.priority):
                time.sleep(4)
                return
    
                         
                  
                         


        
#A generic Valve Class 
class Valve:
        def __init__(self, name, valve_pin, pos):
            self.name = name
            self.lock = threading.Lock()
            self.valvepin = valve_pin
            self.height = 500 #TODO: Add the current height
            self.aperture_area = math.pi*.25 #TODO: Add the cross sectional area
            self.tank_area = math.pi*4 #TODO: Add the tank area
            self.pour_amount = 100 #TODO: Fill in amount to pour
 #TODO: Add the carts
            self.rh_distance = pos #TODO: Set distance from right hand
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(self.valvepin, GPIO.OUT)
            
        def add(self):
            self.lock.acquire()
            return self

        def release(self):
            self.lock.release()
            return
       
        def pour(self, cart, system):
            #self.lock.acquire()
            cart.is_pouring = True
            start = time.time()
            l = 0
            while(l < self.pour_amount): 
                GPIO.output(self.valvepin, GPIO.HIGH) #Opening
                height = self.calculateflow(self.curr_time(start), self.height)
                l =  l+ self.height - height 
                self.height = height
                if(cart.bump_sensor == 0 and system.bump_compliment == 1):
                       cart.runMotor(0)
                #         #print("Check A")
                       system.deadlock_handler(cart)
                       system.complimentary_lock.acquire()
                       system.bump_compliment = 0
                       system.complimentary_lock.release()
                        
                #     #self.curr_pos = self.curr_pos - (time.time()-start)*self.speed
                if(cart.bump_sensor == 1 and system.bump_primary == 1):
                       cart.runMotor(0)
                        #print("Check B")
                #       time.sleep(3)
                       system.deadlock_handler(cart)
                       system.primary_lock.acquire()
                       system.bump_primary = 0
                       system.primary_lock.release()
                #print("Poured " + str(l))
                time.sleep(0.01)

            GPIO.output(self.valvepin, GPIO.LOW)  
            cart.is_pouring = False    #Close 
            #self.lock.release()                
            return

        def curr_time(self, start):
            return time.time()-start

       
       

#Based on the Bernoulli and Toricelli fluid laws. Height is calculated as a solution to a first-order diff. eqn.
        def calculateflow(self, elapsed_time, height):
            c_c = 0.97 #coefficient of contraction
            c_v = 0.97 #coefficient of water vel.
            c_d = c_c*c_v #coefficient of discharge
            height_eqn = math.pow(math.pow(height, 0.5) - ((self.tank_area)/(2*self.aperture_area))* (math.pow(4.9, 0.5) * .01), 2) 
            #return c_d*c_c*3.14*pi*math.pow(2*9.8*height_eqn, 0.5) * elapsed_time
            return height_eqn

#Extending the Valve Class since Ice is not a Liquid
class IceValve(Valve):
        def chunk_out(self, cart):
            start = time.time()
            while(time.time()-start < seconds):
                 GPIO.output(self.valvepin, GPIO.HIGH)

            GPIO.output(self.valvepin, GPIO.LOW)
            return
                            
            
#A generic drink type as specified in the order       
class Drink:
        def __init__(self, DrinkId, onTheRocks, lightIce, mockTail):
            self.liq1 = "None"
            self.liq2 = "None"
            self.liq3 = "None"
            self.liq4 = "None"
            if(DrinkId == 0):
                self.liq1 = "Cranberry"
                self.liq2 = "Vodka"
            elif (DrinkId == 1):
                self.liq1 = "Rum"
                self.liq2 = "Coke"
            elif (DrinkId == 2):
                self.liq2 = "Cranberry"
                self.liq3 = "Coke"
            if(onTheRocks != 0):
                self.liq4 = "Ice-2"
            elif(lightIce != 0):
                self.liq4 = "Ice-1"
            if(mockTail != 0):
                print("NO!")
                self.liq1 = "None"
            self.priority = 0
            print(self.liq1)
            print(self.liq2)
            return                 


#Orderqueue = Queue(20)

def callback(message, channel):
    global Orderqueue
    print("Received the drink")
    toqueue = Drink(int(message["DRINK id"]), int(message["onTheRocksOption"]), int(message["lightIceOption"]), int(message["mocktailOption"]))
    Orderqueue.enqueue(toqueue)
    
    #thread1.exit()


def connect(message):
    print("Pubnub connected")

def error(m):
    print(m)

                    
#General method that calls check_for_orders, travels to the valve, receives the liquid, and returns to the starting position
#Build the queue
   
def main1(cart_arg, system):
    #print("AT THE VERY TOP of main1")
    print(str(cart_arg.lvl));
    if(cart_arg.lvl == 1):
        #print("Check 1")
        #print(cart_arg.drink.liq1)
        if(cart_arg.drink.liq1 == "Vodka"):
          cart_arg.valve = Vodka_Valve.add()
          cart_arg.proceed_to_valve(cart_arg.valve)
          Vodka_Valve.pour(cart_arg, system)
          #cart_arg.return_to_idle()
          Vodka_Valve.release()
          cart_arg.valve = None
        elif(cart_arg.drink.liq1 == "Rum"):
          cart_arg.valve = Rum_Valve.add()
          cart_arg.proceed_to_valve(cart_arg.valve)
          Rum_Valve.pour(cart_arg, system)
          #cart_arg.return_to_idle()
          Rum_Valve.release()
          cart_arg.valve = None
        elif(cart_arg.drink.liq1 == "Cranberry"):
          cart_arg.valve = Cranberry_Valve.add()
          cart_arg.proceed_to_valve(cart_arg.valve)
          Cranberry_Valve.pour(cart_arg, system)
          #cart_arg.return_to_idle()
          Cranberry_Valve.release()
          cart_arg.valve = None
        elif(cart_arg.drink.liq1 == "Coke"):
          cart_arg.valve = Coke_Valve.add()
          cart_arg.proceed_to_valve(cart_arg.valve)
          Coke_Valve.pour(cart_arg, system)
          #cart_arg.return_to_idle()
          Coke_Valve.release()
          cart_arg.valve = None
        elif(cart_arg.drink.liq1 == "Tea"):
          cart_arg.valve = Tea_Valve.add()
          cart_arg.proceed_to_valve(cart_arg.valve)
          Tea_Valve.pour(cart_arg, system)
          #cart_arg.return_to_idle()
          Tea_Valve.release()
          cart_arg.valve = None
        cart_arg.lvl = cart_arg.lvl+1
        system.set_deadlock_flag(0)
        main1(cart_arg, system)
        cart_arg.lvl = cart_arg.lvl-1
        return
    if(cart_arg.lvl == 2):
      #print("Check 3")
      #print(cart_arg.drink.liq2)
      if(cart_arg.drink.liq2 == "Vodka"):
        #print("Check 4")
        cart_arg.valve = Vodka_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Vodka_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Vodka_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq2 == "Rum"):
        cart_arg.valve = Rum_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Rum_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Rum_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq2 == "Cranberry"):
        cart_arg.valve = Cranberry_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Cranberry_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Cranberry_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq2 == "Coke"):
        cart_arg.valve = Coke_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Coke_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Coke_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq2 == "Tea"):
        cart_arg.valve = Tea_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Tea_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Tea_Valve.release()
        cart_arg.valve = None
      cart_arg.lvl = cart_arg.lvl + 1
      system.set_deadlock_flag(0)
      main1(cart_arg, system)
      cart_arg.lvl = cart_arg.lvl - 1
      #print(str(cart_arg.lvl));
      return
    if(cart_arg.lvl == 3):
      if(cart_arg.drink.liq3 == "Vodka"):
        cart_arg.valve = Vodka_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Vodka_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Vodka_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq3 == "Rum"):
        cart_arg.valve = Rum_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Rum_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Rum_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq3 == "Coke"):
        cart_arg.valve = Coke_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Coke_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Coke_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq3 == "Cranberry"):
        cart_arg.valve = Cranberry_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Cranberry_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Cranberry_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq3 == "Tea"):
        cart_arg.valve = Tea_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Tea_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Tea_Valve.release()
        cart_arg.valve = None
      cart_arg.lvl = cart_arg.lvl + 1
      system.set_deadlock_flag(0)
      main1(cart_arg, system)
      cart_arg.lvl = cart_arg.lvl -1
      #print(str(cart_arg.lvl));
      return
    if(cart_arg.lvl == 4):
      if(cart_arg.drink.liq4 == "Vodka"):
        cart_arg.valve = Vodka_Valve.add()
        Vodka_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Vodka_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq4 == "Rum"):
        cart_arg.valve = Rum_Valve.add()
        Rum_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Rum_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq4 == "Coke"):
        cart_arg.valve = Coke_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Coke_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Coke_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq4 == "Cranberry"):
        cart_arg.valve = Cranberry_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Cranberry_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Cranberry_Valve.release()
        cart_arg.valve = None
      elif(cart_arg.drink.liq4 == "Tea"):
        cart_arg.valve = Tea_Valve.add()
        cart_arg.proceed_to_valve(cart_arg.valve)
        Tea_Valve.pour(cart_arg, system)
        #cart_arg.return_to_idle()
        Tea_Valve.release()
        cart_arg.valve = None
      system.set_deadlock_flag(0)
      #print(str(cart_arg.lvl));
      system.delete_drink(cart_arg)
      cart_arg.return_to_idle()
      time.sleep(2)
      cart_arg.lvl = cart_arg.lvl-1
      return
    return
            

def realmain(cart_arg, system):
    global Orderqueue
    while(True):
        #print(str(cart_arg.lvl))
        if(cart_arg.check_for_orders(Orderqueue, system) == False and cart_arg.lvl == 0):
            #print("entered no queue")
            continue
        elif(cart_arg.lvl != 0):
            #print("RIGHT HERE")
            main1(cart_arg, system)
        
        #print("im In the loop")
    #print("Exited the loop D:")
    return

  

try:                    
    #Start-up sequence
    pubnub = Pubnub(
        publish_key = "pub-c-7234b15f-4a3c-4a8f-a352-1e5ec62a1e82",
        subscribe_key = "sub-c-f32f163a-8214-11e5-a4dc-0619f8945a4f")
    channel = "my_channel"

    #TODO: Add pins to the valves
    Vodka_Valve = Valve("VodkaValve", 29, 5.5)
    Rum_Valve = Valve("RumValve", 32, 11)
    Cranberry_Valve = Valve("CranberryValve", 15, 16.5)
    Coke_Valve = Valve("CokeValve", 13, 22)
    Fifth_Valve = Valve("FifthValve", 11, 27.5)




    #Add the carts to the Valve cart attr.


    #Build the queue
    Orderqueue = Queue(20)

    System = System()


    #Build + Add the carts to the sys
    Cart1 = Cart.Cart(37, 38, 40, 18, 0, 1, System)
    Cart2 = Cart.Cart(35, 33, 31, 16, 33, 0, System)

    System.carts = [Cart1, Cart2]
    
                        
    #Connection
    print(str(Cart1 is System.carts[0]))
    print(str(Cart2 is System.carts[1]))
    

    #start the threads
    thread1 = threading.Thread(target = realmain, args = (Cart1, System,))
    thread2 = threading.Thread(target = realmain, args = (Cart2, System, ))
    thread1.start()
    thread2.start()

    pubnub.subscribe(
        channel,
        callback = callback,
        error = error,
        connect = connect)
    print("exit main thread")
    #thread2.start()
    print("Threads started")
except KeyboardInterrupt:
    print("EXIT")









    

