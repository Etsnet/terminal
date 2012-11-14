#!/usr/bin/python
# Based on miniterm sample in pyserial

import sys
import os
import serial
import threading
import traceback
import time
import colorama

colorama.init()

if os.name == 'nt':
    import msvcrt
    class Console:
        def __init__(self):
            pass
        def cleanup(self):
            pass
        def getkey(self):
            while 1:
                z = msvcrt.getch()
                if z == '\0' or z == '\xe0': # function keys
                    msvcrt.getch()
                else:
                    if z == '\r':
                        return '\n'
                    return z
elif os.name == 'posix':
    import termios, sys, os
    class Console:
        def __init__(self):
            self.fd = sys.stdin.fileno()
            try:
                self.old = termios.tcgetattr(self.fd)
                new = termios.tcgetattr(self.fd)
                new[3] = new[3] & ~termios.ICANON & ~termios.ECHO & ~termios.ISIG
                new[6][termios.VMIN] = 1
                new[6][termios.VTIME] = 0
                termios.tcsetattr(self.fd, termios.TCSANOW, new)
            except termios.error:
                # ignore errors, so we can pipe stuff to this script
                pass
        def cleanup(self):
            try:
                termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old)
            except:
                # ignore errors, so we can pipe stuff to this script
                pass
        def getkey(self):
            c = os.read(self.fd, 1)
            return c
else:
    raise ("Sorry, no terminal implementation for your platform (%s) "
           "available." % sys.platform)

class Miniterm:
    """Normal interactive terminal"""

    def __init__(self, serial):
        self.serial = serial
        self.threads = []

    def start(self):
        self.alive = True
        # serial->console
        self.threads.append(threading.Thread(target=self.reader))
        # console->serial
        self.console = Console()
        self.threads.append(threading.Thread(target=self.writer))
        # start them
        for thread in self.threads:
            thread.daemon = True
            thread.start()

    def stop(self):
        self.alive = False

    def join(self):
        for thread in self.threads:
            thread.join()

    def reader(self):
        """loop and copy serial->console"""
        try:
            while self.alive:
                data = self.serial.read(1)
                if not data:
                    continue
                sys.stdout.write(data)
                sys.stdout.flush()
        except Exception as e:
            traceback.print_exc()
            self.console.cleanup()
            os._exit(1)

    def writer(self):
        """loop and copy console->serial until ^C"""
        try:
            while self.alive:
                try:
                    c = self.console.getkey()
                except KeyboardInterrupt:
                    c = '\x03'
                if c == '\x03':
                    self.stop()
                    return
                elif c == '':
                    # EOF on input.  Wait a tiny bit so we can
                    # flush the remaining input, then stop.
                    time.sleep(0.25)
                    self.stop()
                    return
                else:
                    self.serial.write(c)                    # send character
        except Exception as e:
            traceback.print_exc()
            self.console.cleanup()
            os._exit(1)

    def run(self):
        saved_timeout = self.serial.timeout
        self.serial.timeout = 0.1
        self.start()
        self.join()
        print ""
        self.console.cleanup()
        self.serial.timeout = saved_timeout

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simple serial terminal.  "
                                     "If two devices are provided, output from "
                                     "the first is shown in yellow, second in "
                                     "cyan, and input is discarded.")
    parser.add_argument('device', metavar='DEVICE',
                        help='serial device 1')
    parser.add_argument('baudrate', metavar='BAUDRATE', type=int, nargs='?',
                        help='baud rate 1', default=115200)
    parser.add_argument('device2', metavar="DEVICE2", nargs='?',
                        help='serial device 2', default=None)
    parser.add_argument('baudrate2', metavar='BAUDRATE2', type=int, nargs='?',
                        help='baud rate 2', default=115200)
    args = parser.parse_args()
    try:
        dev = serial.Serial(args.device, args.baudrate)
    except serial.serialutil.SerialException:
        sys.stderr.write("error opening %s\n" % args.device)
        raise SystemExit(1)
    print args.device + ", " + str(args.baudrate) + " baud"
    print "^C to exit"
    print "--"
    term = Miniterm(dev)
    term.run()

