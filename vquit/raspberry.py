# Raspberry Pi remote access
class RaspberryPi:

    # Function runs when initializing class
    # Connect to Raspberry and configure I/O
    def __init__(self, Config_module=None):
        # Import time library
        from time import sleep
        self.sleep = sleep

        # Get parameters from configuration file
        ssh_Config = Config_module.Get("Raspberry")["SSH"]
        ip = Config_module.Get("Raspberry")["IP_addr"]
        ssh_Port = ssh_Config["Port"]
        ssh_User = ssh_Config["User"]
        ssh_Pass = ssh_Config["Pass"]

        # Setting up SSH class
        self.ssh = SSH(ip, ssh_Port, ssh_User, ssh_Pass)

        # Kill any leftovers from previous instances and restart GPIO Daemon
        print('Initializing Raspberry IO via SSH...', end='\r')
        with self.ssh:
            self.StopDaemon()
            self.StartDaemon()

        # Raspberry GPIO controller
        print("Importing PiGPIO module")
        import pigpio as gpio
        self.gpio = gpio

        # Connect to pi gpio
        print('Connecting to Raspberry IO...', end='\r')
        self.rpi = self.gpio.pi(ip)  # VQuIT-RemoteIO

        # Setup pin configuration
        print("Setting up Raspberry PinModes...", end="\r")
        try:
            self.PinMode(4, 'input')
        except:
            print(
                "\nError connecting to Raspberry.\nCheck if VQuIT_Config.json>Raspberry>IP_addr has the same IP as inet when running 'ifconfig' on the Raspberry\n")
        print(" ", end='\n')

    def Disconnect(self):
        # Disconnect IO
        print("Disconnecting from Raspberry IO...", end="\r")
        self.rpi.stop()

        # Stop GPIO Daemon
        print("Stopping Raspberry IO via SSH...", end="\r")
        with self.ssh:
            self.StopDaemon()

        # Ask user whether to shutdown or disconnect the Raspberry
        shutdownPrompt = input("Shutdown Raspberry? (y/n)")
        if shutdownPrompt is "y":
            with self.ssh:
                self.ShutdownPi()
            print("Shutdown Raspberry successfully")
        else:
            print("Disconnected from Raspberry successfully")

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

    #################
    # SSH Functions #
    #################

    # Start Daemon to use Raspberry GPIO
    def StartDaemon(self):
        self.ssh.Send('sudo pigpiod')
        self.sleep(3)

    # Stop Daemon when done with Raspberry GPIO
    def StopDaemon(self):
        self.ssh.Send('sudo killall pigpiod')

    # Shutdown Raspberry when shutting down tool
    def ShutdownPi(self):
        print("Shutting down Raspberry")
        self.ssh.Send('sudo shutdown -h now')


# Connect to clients via SSH
class SSH:

    # Function runs when initializing class
    def __init__(self, ip, port, username, password):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.client = None

        print("Importing paramiko SSH module")
        import paramiko
        self.ssh = paramiko

    # Function runs when using class in a "with" statement
    def __enter__(self):
        print('Connecting to Raspberry terminal via SSH...', end='\r')

        self.client = self.ssh.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(self.ssh.AutoAddPolicy())
        self.client.connect(self.ip, port=self.port, username=self.username, password=self.password)

    # Function runs at the end of a "with" statement
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Stopping SSH connection...", end="\r")
        self.client.close()

    def Send(self, command, printReturn=None):

        stdin, stdout, stderr = self.client.exec_command(command)

        if printReturn is True:
            # Print return
            for line in stdout:
                print('SSH: ' + line.strip('\n'))

            # Print errors
            for line in stderr:
                print('SSH: ' + line.strip('\n'))
        return stdout, stderr
