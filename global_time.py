import ntplib

NTP_CLIENT = ntplib.NTPClient()

def time():
    try:
        return NTP_CLIENT.request('pool.ntp.org', version=3).tx_time
    except:
        return None