#############################################################################
# README:
#   Platform:       CentOS 6.7 
#   Python:         3.6.8
#   Required:       
#   Check Speed:    sudo apt-get install sysstat 
#                   cmd=> sar -n DEV 1 100
# 
#   Description:    base on test-v5
#                   
#   requirement:    aim at : check continuosly lose 5 packet
#############################################################################


#############################################################################
#   import
#############################################################################

import socket
import time
import csv
import os
import struct 
import sys
import threading
import tkinter
import tkinter.messagebox
from prettytable import PrettyTable
from argparse import ArgumentParser

#############################################################################
#   translation type functions:
#############################################################################

def bytes_to_int( bytes_data ):
	int_data = int.from_bytes( bytes_data, byteorder='big', signed=False )
	return int_data

def int_to_bytes( int_data, length = 10 ):
	bytes_data = int_data.to_bytes( length, "big", signed=False )
	return bytes_data


#############################################################################
#   Parameters:
#############################################################################

BUFSIZE     =   1024            # receive packet size
ETH_P_DEF   =   0x8874	        # user defined
Board_MAC   =   b'\xc0\xb1\x3c\x88\x88\x90'
Centos_MAC  =   b'\x00\x0c\x29\xbc\xad\xce'
Ubuntu_MAC  =   b'\x00\x0c\x29\x18\x7c\x12'
Type_DEF    =   b'\x88\x74' 
numberID    =   1               #send id is odd number, receive id is even number
# ETH_P_IP    = 0x0800	        #IP type 
# type_IP     = b'\x08\x00'

NIC         =   "eth0"
check_type  =   Type_DEF
Dst_MAC     =   Board_MAC
Src_MAC     =   Centos_MAC
server_proto =  socket.htons(ETH_P_DEF)
#fixme:what if packet should be received but type not 8874??
client_proto =  socket.htons(ETH_P_DEF)


#############################################################################
#   cmd Parameters:
#############################################################################

parser = ArgumentParser(description='Set some parameters or use default setting .')

parser.add_argument("--loop", help="how many times execute in one loop,\
     default is 100 .", type = int)
parser.add_argument("--timewait", help="after send thread done and wait \
    for recv thread time, default is 2 .", type = int)
parser.add_argument("--timeahead", help="send thread ahead of recv thread's time\
    , default is 0 second .", type = int)
parser.add_argument("--times", help="execute n loops\
    , default is 1 .", type = int)
parser.add_argument("--ms", help="wait ms microsecond in order to\
     match recv speed , default is 10 microsecond .", type = int)   
parser.add_argument("--data", help="the data in the packet[20:1024] int number\
     , default is 17 0x11, please less than 0xff .", type = int)   
# parser.add_argument("-file", help="whether to write to a file ,\
#     default is able", action="store_true")
parser.add_argument('-v','--verbose', help="display more information during execution,\
    default is disable", action="store_true")
parser.add_argument("-Ubuntu", help="check sqhuang's ubuntu,\
    default is not", action="store_true")
parser.add_argument("-error", help="actively inject error data in every loop,\
     default is data + 1", action="store_true")

args = parser.parse_args()

if args.timewait:
    time_wait = args.timewait
else:
    time_wait = 2

if args.timeahead:
    time_ahead = args.timeahead
else:
    time_ahead = 0

if args.loop:
    loop_size = args.loop
else:
    loop_size = 100

if args.times:
    loop_times = args.times
else:
    loop_times = 1 

if args.ms:
    ms = args.ms
else:
    ms = 10

if args.data:
    data_init = args.data
else:
    data_init = 17

# if args.file:
#     file_enable = True
# else:
#     file_enable = False
# default: file write able
file_enable = True

if args.verbose:
    verbose = True
else:
    verbose = False

if args.Ubuntu:
    NIC = "ens39"
    check_type = Type_DEF
    Dst_MAC = Board_MAC
    Src_MAC = Ubuntu_MAC
    server_proto = socket.htons(ETH_P_DEF)
    client_proto = socket.htons(ETH_P_DEF)
else:
    pass

if args.error:
    error_inject    =   True
else:
    error_inject    =   False

#############################################################################
#   output file:
#############################################################################
if file_enable:
    filename = 'Ethernet-' + time.strftime("%H.%M.%S") + '-' + 'log'
    f_eth = open( filename + ".csv", mode = "w")
    writer  =   csv.writer(f_eth)

    writer.writerow(["time","timestamp","send","receive","miss","lose_rate(%)","bit_error"])
    f_eth.flush()
    # tb = PrettyTable()
    # tb.field_names = ["time","send","receive","miss","bit error"]
else:
    pass

###############################################################################
#   Socket  :
###############################################################################
client_eth = socket.socket()       
host = socket.gethostname()        
user_port = 4877                    

WARNING_5BitError   =   b'\xa1'
WARNING_5PacketLose =   b'\xa2'

global sock_flag
link_down_count =   1
sock_flag       =   1
while(True):
    try: 
        assert (link_down_count < 5)
        client_eth.connect((host, user_port))     
        link_down_count = 1
        break
    except OSError:
        print('Can not link tk server in %d times. Reconnect ...'%link_down_count)
        link_down_count += 1
        time.sleep(1)
    except AssertionError:
        print('Can not link tk socket server in 10 second.')
        xx = input('Press "e" to exit, "r" to retry, or other key to ignore and continue ... :')
        if( xx == 'e'):
            sock_flag   =   0
            exit()
        elif( xx == 'r'):
            link_down_count = 1
            continue
        else:
            sock_flag   =   0
            break

#############################################################################
#   loop buffer:
#############################################################################
count = 1
SEND_DONE = 0       # send thread to recv thread signal, force to stop recv thread

# BUFFER_send         =   []
# BUFFER_send_store   =   []
BUFFER_recv         =   []
BUFFER_recv_store   =   []
# BUFFER_CHECK        =   []
BUFFER_ID           =   []
  
global Bit5Error
global LinkDown
LinkDown            =   0
Bit5Error           =   0
#############################################################################
#   Packet related:
#############################################################################
header          =   struct.pack("6s6s2s", Dst_MAC, Src_MAC, Type_DEF )
pad             =   b'\x11\x11'

numberID_bytes  =   int_to_bytes( numberID, 4 )
number          =   struct.pack( "4s",numberID_bytes[::-1] )

send_data       =   bytes(1003) + int_to_bytes( data_init, 1 )
data_packet     =   header + pad + number + send_data



#############################################################################
#   thread functions:
#############################################################################
def recv():
    global SEND_DONE 
    global BUFFER_recv
    global BUFFER_recv_store
    global count_recv

    print('')
    print("Entering recv function!!!")

    for _ in range(loop_size):  # initialize with 0
        # BUFFER_recv.append(0)
        BUFFER_ID.append(0)

    count_recv = 0
    while(count_recv < loop_size):

        # print('wait for receiving the Num.%d Packet .' %(count_recv+1) )
        
        if( SEND_DONE == 0 ):
            try:
                Packet_recv = clientPC.recv(BUFSIZE)

                print("--------Num.%d Packet is received--------" %(count_recv+1) )
                print("Receive packet type is : ",end='')
                print( struct.unpack( "!2s", Packet_recv[12:14] ) )

                recv_id_bytes   =    Packet_recv[16:20]
                recv_id_bytes   =    recv_id_bytes[::-1]             # reverse order
                recv_id_int     =    bytes_to_int(recv_id_bytes)
                BUFFER_ID[count_recv] = recv_id_int
                BUFFER_recv.append(Packet_recv) 

                count_recv  +=  1
            except BlockingIOError:
                pass
            except KeyboardInterrupt:
                print("Keyboard Interruption happen during recv thread !")
                time.sleep(0.5)
            except:
                print("Something unexpected during recv thread !")
                time.sleep(0.5)

        else:
            print('Ready to close recv thread. ')
            break

    BUFFER_recv_store = BUFFER_recv.copy()
    BUFFER_recv.clear() 
    SEND_DONE = 0
    print('Recv thread is done!!!')

def recv_simple():
    global SEND_DONE 
    global BUFFER_recv
    global BUFFER_recv_store
    global count_recv

    for _ in range(loop_size):  # initialize with 0
        # BUFFER_recv.append(0)
        BUFFER_ID.append(0)

    count_recv = 0
    while(count_recv < loop_size):
        if( SEND_DONE == 0 ):
            try:
                Packet_recv = clientPC.recv(BUFSIZE)
                # print("--------Num.%d Packet is received--------" %(count_recv+1) )
                recv_id_bytes   =    Packet_recv[16:20]
                recv_id_bytes   =    recv_id_bytes[::-1]             # reverse order
                recv_id_int     =    bytes_to_int(recv_id_bytes)
                BUFFER_ID[count_recv] = recv_id_int
                BUFFER_recv.append(Packet_recv) 
                count_recv  +=  1
            except BlockingIOError:
                pass
            except KeyboardInterrupt:
                print("Keyboard Interruption happen during recv thread !")
                time.sleep(0.5)
            except:
                print("Something unexpected during recv thread !")
                time.sleep(0.5)
        else:
            print('Ready to close recv thread. ')
            break

    BUFFER_recv_store = BUFFER_recv.copy()
    BUFFER_recv.clear() 
    SEND_DONE = 0
    print('Recv thread is done!!!')

def send():
    global SEND_DONE 
    # global BUFFER_send
    # global BUFFER_send_store
    global numberID
    global count_send

    print('')
    print("Entering send function!!!")

    # for _ in range(loop_size):  # initialize with 0
    #     BUFFER_send.append(0)

    count_send = 0
    while(count_send < loop_size):
        try:
            numberID_bytes = int_to_bytes( numberID , 4 )
            number = struct.pack( "4s",numberID_bytes[::-1] )

            
            if(error_inject):
                if(count_send == (loop_size-2) ):
                    error_int   =  data_init + 1
                    error_bytes =  int_to_bytes( error_int, 1 ) 
                    error_data  =  bytes(1003) + error_bytes 
                    data_packet =  header + pad + number + error_data
                else:
                    data_packet =  header + pad + number + send_data
            else:
                data_packet =  header + pad + number + send_data

            server.send(data_packet)
            # print( "*******Num.%d Data is sending..."%(count_send+1) )

            # BUFFER_send[count_send] = data_packet
            count_send  +=  1
            numberID    +=  2
            time.sleep(0.001 * ms)

        except BlockingIOError:
            pass
        except KeyboardInterrupt:
            print("Keyboard Interruption happen during send thread !")
            time.sleep(0.5)
        except:
            print("Something unexpected during send thread !")
            time.sleep(0.5)



    time.sleep(time_wait)
    SEND_DONE = 1
    # BUFFER_send_store = BUFFER_send.copy()

    # BUFFER_send.clear()

    print('Send thread is done!!!')
    print('')

def send_simple():
    global SEND_DONE 
    global numberID
    global count_send
    print('')
    print("Entering send function!!!")

    count_send = 0
    while(count_send < loop_size):
        try:
            numberID_bytes = int_to_bytes( numberID , 4 )
            number = struct.pack( "4s",numberID_bytes[::-1] )

            if(error_inject):
                if(count_send == (loop_size-2) ):
                    error_int   =  data_init + 1
                    error_bytes =  int_to_bytes( error_int, 1 ) 
                    error_data  =  bytes(1003) + error_bytes 
                    data_packet =  header + pad + number + error_data
                else:
                    data_packet =  header + pad + number + send_data
            else:
                data_packet =  header + pad + number + send_data

            server.send(data_packet)
            # print( "Num.%d Data is sending..."%(count_send+1) )
            count_send  +=  1
            numberID    +=  2
            time.sleep(0.001 * ms)
        except BlockingIOError:
            pass
        except KeyboardInterrupt:
            print("Keyboard Interruption happen during send thread !")
            time.sleep(0.5)
        except:
            print("Something unexpected during send thread !")
            time.sleep(0.5)

    time.sleep(time_wait)
    SEND_DONE = 1

    print('Send thread is done!!!')
    print('')


def test_speed():
# display order: receive packet k/s, transfer packet k/s, receive kB/s, transfer kB/s
    print('')
    cmd = 'sar -n DEV 1 5 |grep ' + NIC
    os.system(cmd)

def check():
    global bit_error
    global Bit5Error
    global LinkDown
    global sock_flag

    LinkDown    =   0
    Bit5Error   =   0
    bit_error   =   0

    print('')
    print('Enter check thread : ')
    print('Buffer size is %d'%(len(BUFFER_recv_store)))

    for ii in range( len(BUFFER_recv_store) ):
        check_raw( BUFFER_recv_store[ii] )

    check_number(BUFFER_recv_store)

    if(bit_error >= 5):
        Bit5Error = 1
    else:
        Bit5Error = 0
    
    if ( sock_flag & (Bit5Error == 1) ):
        try:
            warn_info = WARNING_5BitError
            print("Ready to send ethernet warning...")
            client_eth.send(warn_info)
        except OSError:
            print('Can not link socket server.')
            sock_flag = 0
            client_eth.close()
        except KeyboardInterrupt:
            print('User have press Ctrl+C during ethernet loop .')
            client_eth.close()
            f_eth.close()
            server.close()
            clientPC.close()
            exit()

    if ( sock_flag & (LinkDown == 1) ):
        try:
            warn_info = WARNING_5PacketLose
            print("Ready to send ethernet warning...")
            client_eth.send(warn_info)
        except OSError:
            print('Can not link socket server.')
            sock_flag = 0
            client_eth.close()
        except KeyboardInterrupt:
            print('User have press Ctrl+C during ethernet loop .')
            client_eth.close()
            f_eth.close()
            server.close()
            clientPC.close()
            exit()

    BUFFER_recv_store.clear()

    # fix:me
    tb = PrettyTable()
    tb.field_names = ["time","send","receive","miss","lose percent","bit error"]
    tb.add_row([time.strftime("%H:%M:%S"),count_send,count_recv,\
        (loop_size-count_recv),round( (loop_size-count_recv)*100/loop_size, 2),\
            bit_error ])
    print(tb)
    print('check done .')

def check_raw( packet_in ):
    global bit_error

# source and destination must change position due to the send and receive direction
    if( packet_in[0:6] != Src_MAC ):
        check_bit( packet_in[0:6], Src_MAC )
    else:
        pass

    if( packet_in[6:12] != Dst_MAC ):
        check_bit( packet_in[6:12], Dst_MAC )
    else:
        pass

    if( packet_in[12:14] != Type_DEF ):
        check_bit( packet_in[12:14], Type_DEF )
    else:
        pass

    if( packet_in[14:16] != pad ):
        check_bit( packet_in[14:16], pad )
    else:
        pass

    if( packet_in[20:1024] != send_data ):
        check_bit( packet_in[20:1024], send_data )
    else:
        pass


def check_bit( under_check, golden ):
    global bit_error
    flag = 0
    under_check_int = int.from_bytes( under_check, byteorder = 'big', signed = False )
    under_check_bin = bin(under_check_int)

    golden_int = int.from_bytes( golden, byteorder = 'big', signed = False )
    golden_bin = bin(golden_int)

    length_max  =   max( len(under_check_bin), len(golden_bin) )

    while ( len(under_check_bin) < length_max ):
        list_u          =   list(under_check_bin)
        list_u.insert(2,'0')
        under_check_bin =   ''.join(list_u)

    while ( len(golden_bin) < length_max ):
        list_g          =   list(golden_bin)
        list_g.insert(2,'0')
        golden_bin      =   ''.join(list_g)
        
    for i in range( len(golden_bin) ):
        if ( under_check_bin[i] != golden_bin[i] ) :
            bit_error += 1
            flag = 1
        else:
            pass

    if (flag):
        print('While golden is : ',end = '')
        print(golden)
        print('But packet is : ',end = '')
        print(under_check)    
    else:
        pass

def check_number(Buffer):
    global LinkDown
    Buffer_number = []
    check_buffer = []

    for i in range(len(Buffer)):
        Buffer_this = Buffer[i]
        Buffer_num = Buffer_this[16:20]
        Buffer_num = Buffer_num[::-1]
        int_this = bytes_to_int(Buffer_num)
        Buffer_number.append( int_this )
    

    if(Buffer_number[-1] < loop_size*2-12):
        if((Buffer_number[-2] < loop_size*2-14) ):
            print('Link down at last transfer: ',end='')
            print(Buffer_number[-1])
            LinkDown = 1
        else:
            pass
    else:
        pass

    for ii in range( len(Buffer_number) -1 ):
        check_buffer.append( Buffer_number[ii+1] - Buffer_number[ii] )
    
    for iii in range( len(check_buffer) ):
        if( check_buffer[iii] > 12 ):
            if( iii != (len(check_buffer)-1) ):
                if( check_buffer[iii+1] > 0 ):
                    print('Link down at middle transfer. ')
                    # print(check_buffer[iii])
                    LinkDown = 1
                else:
                    if( (check_buffer[iii+1] + check_buffer[iii]) > 14):
                        print('Link down at middle transfer. ')
                        # print(check_buffer[iii])
                        LinkDown = 1
                    pass
            else:
                LinkDown = 1
        else:
            pass


    Buffer_number.clear()
    check_buffer.clear()



#############################################################################
#   Main:
#############################################################################

#FIXME:socket.htons(ETH_P_DEF) SHOULD BE ANY NUMBE
server          =   socket.socket( socket.PF_PACKET, socket.SOCK_RAW, server_proto ) 
clientPC        =   socket.socket( socket.PF_PACKET, socket.SOCK_RAW, client_proto )
server.bind( (NIC, server_proto ) )
clientPC.setblocking(False)         # receive timout = 0, non-block receive

# print("Initial data_packet : "),
# print( struct.unpack( str(len(data_packet)) + "s", data_packet) )
print("Ready.")
print('----------------------------------------------------------')


while(count <= loop_times):
#************************ threads start ************************
#sar.start()
    try:
    # thread allocate

        if(verbose):
            t_recv  =   threading.Thread( target=recv, daemon = True )
            t_send  =   threading.Thread( target=send, daemon = True )
        else:
            t_recv  =   threading.Thread( target=recv_simple, daemon = True )
            t_send  =   threading.Thread( target=send_simple, daemon = True )

        t_check =   threading.Thread( target=check, daemon = True )
        # sar     =   threading.Thread( target=test_speed, daemon = True )

        t_send.start()
        time.sleep(time_ahead)
        t_recv.start()

        #sar.join()
        t_send.join()
        t_recv.join()

        t_check.start()
        t_check.join()

#************************ main thread ************************
        time.sleep(1)
        SEND_DONE = 0

        miss = loop_size - count_recv
        # correct_rate = round( (count_recv/loop_size), 4 )*100
        # print('Complete %.2f %%' %( correct_rate ) )
        print('Main thread loop %d is done .'%count)

        if file_enable:
            newitems = [time.strftime("%H:%M:%S"),round(time.time(),4),count_send,\
                count_recv,miss,round( (miss*100)/loop_size, 2),bit_error]
            # tb.add_row(newitems)
            writer.writerow(newitems)
            f_eth.flush()
        else:
            pass
        count   +=  1

    except KeyboardInterrupt:
        print('User press Ctrl+C to interrupt !')

        if file_enable:
            # f_eth.write( str(tb) )
            f_eth.close()
        else:
            pass

        server.close()
        clientPC.close()
        exit()


server.close()
clientPC.close()

if file_enable:
    # f_eth.write( str(tb) )
    f_eth.close()
else:
    pass

print('Bit5Error is %d .'%Bit5Error)
print('LinkDown is %d .'%LinkDown)
print('All work done .')
