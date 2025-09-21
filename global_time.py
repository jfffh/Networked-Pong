import ntplib

def time():
    c = ntplib.NTPClient()
    response = c.request('europe.pool.ntp.org', version=3)
    response.offset
    return response.tx_time