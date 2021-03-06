###############################################################################
#   Python      :   python 3.6.8
#   Requisite   :   keyboard
#                   prettytable
#
#   unsolved    :   can not enter write function well
###############################################################################

import serial
import time
import struct
import os
import threading
import keyboard
from prettytable import PrettyTable
from argparse import ArgumentParser


def bytes_to_int(recv_data):
    int_num =   int.from_bytes(recv_data, byteorder='big', signed=False)
    return int_num

parser = ArgumentParser(description='Set some parameters or use default setting .')
parser.add_argument("--port", help="set the COM port,\
     default is COM8 .", type = str)
parser.add_argument("--sleep", help="set the sleep time every loop,\
     default is 1 .", type = float)   
args = parser.parse_args()

if args.port:
    port    =   args.port
else:
    port    =   'COM8'

if args.sleep:
    sleep_time    =   args.sleep
else:
    sleep_time    =   1.0
# Use code below to test which port is available
# port_list = list( serial.tools.list_ports.comports() )
# print(port_list)
# if len(port_list) == 0:
#    print('No port available . ')
# else:
#     for i in range(0,len(port_list)):
#         print(port_list[i]) 

READ    =   ( 0b0 << 7 )
WRITE   =   ( 0b1 << 7 )


baudrate    =   9600
timeout     =   None    # None:wait forever; 0:do not wait; n:timeout is n second
READ_SIZE   =   4       # read up to 4 bytes
WRITE_SIZE  =   1       # write data is 8 bit, 1 byte 

#   R
Time            =   0x00
Err_sram        =   0x04
Err_pllser      =   0x05
Err_pllsys      =   0x06
Err_plleth      =   0x07
Err_pll1        =   0x08
Err_pll2        =   0x09
Err_pllcas      =   0x0A
Err_dff         =   0x0B
Err_dffinv      =   0x0C
Err_lane0       =   0x0D
Err_lane1       =   0x0E
Err_linkdown0   =   0x0F
Err_linkdown1   =   0x10
Err_linkrecvy0  =   0x11
Err_linkrecvy1  =   0x12
Err_cpu         =   0x13
Reset_ALL       =   0x1C

#   W/R
Pll_freq        =   0x14
Clr_err_ser     =   0x15
Clr_err_eth     =   0x16
Clr_err_sram    =   0x17
Clr_err_pll     =   0x18
Clr_err_dff     =   0x19
Reset_ser       =   0x1A
Reset_sram      =   0x1B


read_reg        =   [0 for _ in range(18)]
read_reg[0]     =   Time
read_reg[1]     =   Err_sram
read_reg[2]     =   Err_pllser
read_reg[3]     =   Err_pllsys
read_reg[4]     =   Err_plleth
read_reg[5]     =   Err_pll1
read_reg[6]     =   Err_pll2
read_reg[7]     =   Err_pllcas
read_reg[8]     =   Err_dff
read_reg[9]     =   Err_dffinv
read_reg[10]    =   Err_lane0
read_reg[11]    =   Err_lane1
read_reg[12]    =   Err_linkdown0
read_reg[13]    =   Err_linkdown1
read_reg[14]    =   Err_linkrecvy0
read_reg[15]    =   Err_linkrecvy1
read_reg[16]    =   Err_cpu
read_reg[17]    =   Reset_ALL

tb1 = PrettyTable()
tb1.field_names = ["Time","Err_sram","Err_pllser","Err_pllsys","Err_plleth",\
    "Err_pll1","Err_pll2","Err_pllcas","Err_dff"]

tb2 = PrettyTable()
tb2.field_names = ["Err_dffinv","Err_lane0","Err_lane1","Err_linkdown0",\
    "Err_linkdown1","Err_linkrecvy0","Err_linkrecvy1","Err_cpu","Reset_ALL"]

###############################################################################
#   Define functions :
###############################################################################

def user_read( addr ):
    read_signal         =   ( READ | addr )
    read_signal_byte    =   read_signal.to_bytes( 1, "big", signed=False )
    byte_width          =   ser.write( read_signal_byte )
    data_byte           =   ser.read( READ_SIZE )
    data_int            =   bytes_to_int(data_byte)
    # print( data_read )
    # print( struct.unpack( str(len(data_read)) + "s", data_read) )

    try:
        assert  byte_width == 1
    except:
        print('Something wrong during the read function . ')
        return 0 
    
    return data_int

def user_write():
    global write_occur
    while( True ):
        keyboard.wait('1')
        write_info()
    
def write_info():
    global write_occur
    write_occur =   1
    print('please input 1 and another 7 bit address : ',end='')
    addr_info_str   =   input()
    print('please input another 8 bit data : ',end='')
    data_info_str   =   input()

    try:
        assert len(addr_info_str) == 8
        assert len(data_info_str) == 8
    except AssertionError:
        print('Sorry. You have input incorrect bit number . ')
        print('Please input 8 bit binary information, try again . ')
        write_info()

    addr_info_int   =   int( '0b' + addr_info_str, 2 )
    addr_info_byte  =   addr_info_int.to_bytes( 1, "big", signed = False )

    data_info_int   =   int( '0b' + data_info_str, 2 )
    data_info_byte  =   data_info_int.to_bytes( 1, "big", signed = False )

    ser.write(addr_info_byte)
    print('Address information has been sended ! ')
    ser.write(data_info_byte)
    print('Data information has been sended ! ')
    
# exception serial.SerialException
# exception serial.SerialTimeoutException
#     Exception that is raised on write timeouts.

###############################################################################
#   MAIN
###############################################################################

if __name__=='__main__':
    global write_occur

    try:
        ser = serial.Serial( port, baudrate, timeout=timeout ) 
        ser.bytesize    =   8
        ser.open()
        print('COM is open .')
    except serial.SerialException:
        print('Can not found device, raise SerialException .')
    except:
        print('error')

    # try:
    #     ser.is_open() == True
    # except:
    #     print('Serial Port is not open, exit ! ')
    #     exit()

    t_write = threading.Thread( target = user_write, daemon = True)
    t_write.start()

    try:
        while(True):
            write_occur =    0
            
            if( write_occur == 0 ):
                print('read loop')
                # entering read loop

                data_tmp = []
                for reg in read_reg:
                    data_tmp.append( user_read( reg ) )
                    print('Read %d reg done . '%reg)

                # read_signal         =   ( READ | Err_sram )
                # read_signal_byte    =   read_signal.to_bytes( 1, "big", signed=False )
                # print('waiting to send...')
                # byte_width          =   ser.write( read_signal_byte )
                # print('waiting to read...')
                # data_read           =   ser.read( READ_SIZE )
                # int_recv            =   bytes_to_int(data_read)
                # bin_recv            =   bin(int_recv)

                # while ( len(bin_recv) < 32 ):
                #     list_b          =   list(bin_recv)
                #     list_b.insert(2,'0')
                #     bin_recv        =   ''.join(list_g)

                # print(bin_recv)
                # print('read TIME register finish . ')

                row1    =   data_tmp[0:9]
                row2    =   data_tmp[9:18]
                tb1.add_row(row1)
                tb2.add_row(row2)
                print(tb1)
                print(tb2)

                time.sleep( sleep_time )

            else:
                # entering write loop
                time.sleep( sleep_time )

    except KeyboardInterrupt:
        print('Interruption Ctrl+C in main thread, ready to exit . ')

    except :
        print('Unpredictable exception occurs !! ')
        

    ser.close()