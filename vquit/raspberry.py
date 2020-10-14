# Raspberry Pi remote access
class RaspberryPi:
    rpi = None
    gpio = None

    # Connect to Raspberry and configure I/O
    def Setup(self, Config_module=None):

        # Raspberry controller
        import pigpio as gpio
        self.gpio = gpio

        # Connect to pi
        print('Connecting to Raspberry...', end='\r')
        self.rpi = self.gpio.pi(Config_module.Get("Raspberry")["IP_addr"])  # VQuIT-RemoteIO

        # Setup pin configuration
        print("Setting up Raspberry...", end="\r")
        try:
            self.PinMode(4, 'input')
        except:
            print(
                "\nError connecting to Raspberry.\nMake sure to run 'sudo pigpiod' on the Raspberry.\nCheck if VQuIT_Config.json>Raspberry>IP_addr has the same IP as inet when running 'ifconfig' on the Raspberry\n")

    def Disconnect(self):
        self.rpi.stop()

    def PinMode(self, pin, state):
        if state is 'input':
            self.rpi.set_mode(pin, self.gpio.INPUT)
        elif state is 'output':
            self.rpi.set_mode(pin, self.gpio.OUTPUT)
        else:
            print("Bad state for GPIO pin")

    def Write(self, pin, value):
        self.rpi.write(pin, value)

    def Read(self, pin):
        return self.rpi.read(pin)
