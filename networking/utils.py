import time
import ntplib
import threading

NTP_CLIENT = ntplib.NTPClient()

#basic byte buffer
class buffer:
    def __init__(self):
        self.bytearray = bytearray()

    def add_bytes(self, bytes:bytes):
        self.bytearray.extend(bytes)

#ntp time getter
def ntp_time():
    try:
        return NTP_CLIENT.request('pool.ntp.org', version=3).tx_time
    except:
        return None
    
#time manager
class time_manager:
    def __init__(self):
        self.start_time = time.time()
        self.start_ntp_time = ntp_time()

    def time(self):
        return self.start_ntp_time + (time.time() - self.start_time)
    
#threader
def thread(function:object, *args):
    threading.Thread(target=function, args=args).start()