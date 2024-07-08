# xDevs.com Python A3 ADC health test GPIB app for HPAK 3458A 
# (C) 2024 xDevs.com | Illya Tsemenko
# Useful information:
#   https://xdevs.com/guide/life_with_3458/
#   https://xdevs.com/guide/ni_gpib_rpi/
#   https://xdevs.com/fix/hp3458
#   https://xdevs.com/guide/e5810a/

'''
This application runs ACAL every hour on tandem of three HP/Agilent/Keysight 3458A DMMs to verify stability of ADC A3 assembly
Key calibration constants are stored into datafile in same directory as program for further analysis
Deviation of CAL? 72 constant from first day of data by more than 0.02 ppm/day can be considered faulty/bad A3, when not taking temperature coefficient into account.
Drift over 0.05 ppm/day is a telltale of the faulty A3 U180 hybrid ASIC chip. This can be further confirmed by INL sweep on 12V range. 
Some more details explained here: https://xdevs.com/fix/hp3458a/#a3drift, https://xdevs.com/fix/hp3458a/#sn18test
'''

import sys
import time
#from colorama import just_fix_windows_console
#just_fix_windows_console()                 # Activate support for colors in windows console

from rich.logging import RichHandler
from hp_gpib.interface.prologix import find_adapters, Instrument, Prologix

# Setting variables
dmm1_gpib_addr = 22
filename1 = ("n3458a_KOF_gpib_%d_2024_data.csv" % dmm1_gpib_addr)
ip_addr = "192.168.30.10"
hw_interface_type = "vxi"                  # Please select vxi or visa or linux-gpib
timegap = 3600                             # Number of seconds to wait between ACALs
run_hours = 720                            # Run 30 days for stability data (24 * 30 day = 720 hours)

print("\033[44;33m -n- SN18 verification data collection script for HP3458A. (C) xDevs.com 2024\033[49;39m")

try:
    with Prologix(ip_addr) as adapter:
        with Instrument(adapter, int(dmm1_gpib_addr)) as inst:
            print("Prologix adapter connected.")

            # Initialize first 3458A
            inst.cmd("RESET")
            inst.cmd("END ALWAYS")
            inst.cmd("PRESET NORM")
            inst.cmd("OFORMAT ASCII")
            data = inst.cmd("ID?", reply=True)
            print("\033[32;1m -i- %s detected on GPIB %d \033[39;0m" % (data, dmm1_gpib_addr))

    # Function to read calibration values BEFORE running ACAL
    def log_data_pre(ins, files, id):
        data = ins.cmd("TEMP?", reply=True)
        print("\033[37;1m -i- %s internal TEMP? = %s C\r\033[39;0m" % (id, data))
        data = ins.cmd("CAL? 1,1", reply=True)
        data = ins.cmd("CAL? 2,1", reply=True)
        data = ins.cmd("CAL? 72", reply=True)

    # Function to read calibration values AFTER successful ACAL ALL
    def log_data_after(ins, files, id):
        files.write(time.strftime("%d/%m/%Y-%H:%M:%S,"))

        data = ins.cmd("TEMP?", reply=True).decode().strip()
        files.write(data + ',')
        
        data = ins.cmd("CAL? 1,1", reply=True).decode().strip()
        files.write(data + ',')
        
        data = ins.cmd("CAL? 2,1", reply=True).decode().strip()
        files.write(data + ',')
        
        data = ins.cmd("CAL? 78", reply=True).decode().strip()
        files.write(data + ',')
        
        data = ins.cmd("CAL? 79", reply=True).decode().strip()
        files.write(data + ',')
        
        data = ins.cmd("CAL? 70", reply=True).decode().strip()
        files.write(data + ',')
        
        data = ins.cmd("CAL? 86", reply=True).decode().strip()
        files.write(data + ',')
        
        data = ins.cmd("CAL? 87", reply=True).decode().strip()
        files.write(data + ',')
        
        data = ins.cmd("CAL? 176", reply=True).decode().strip()
        files.write(data + ',')
        
        data = ins.cmd("CAL? 59", reply=True).decode().strip()
        files.write(data + ',')
        
        data = ins.cmd("CAL? 97", reply=True).decode().strip()
        files.write(data + ',')
        
        data = ins.cmd("CAL? 72", reply=True).decode().strip()
        files.write(data + '\n')
        
        print("\033[35;1m -i- %s CAL? 72 value = %s \r\033[39;0m" % (id, data))
        # Beep multiple times for user awareness
        #ins.cmd("BEEP")
        #time.sleep(0.1)
        #ins.cmd("BEEP")
        #time.sleep(0.5)
        #ins.cmd("BEEP")
        #time.sleep(1)
        ins.cmd("DISP OFF")

    for cycles in range(0, run_hours): # Perform hours sequence and append each run data into files
        with open(filename1, 'a') as o1:
            # Collect pre-ACAL data
            try:
                with Prologix(ip_addr) as adapter:
                    with Instrument(adapter, int(dmm1_gpib_addr)) as inst:
                        print("Prologix adapter connected.")
                        # Initialize first 3458A
                        log_data_pre(inst, o1, "3458A")

                        # Execute ACAL ALL on all instruments
                        inst.cmd("ACAL ALL")
                        time.sleep(860)  # Wait for 860 seconds while ACAL ALL is running

                        # Collect key CAL constants after ACAL done
                        log_data_after(inst, o1, "3458A")
            except Exception as e:
                print(f"Error during ACAL cycle: {e}")

        print("\033[36;1m -i- ACAL cycle %d done \r\033[39;0m" % (cycles))
        time.sleep(timegap - 860)    # wait for next hour to execute next ACAL iteration

except Exception as e:
    print(f"Error in initial setup: {e}")

print("All done! Check for more at https://xDevs.com")

