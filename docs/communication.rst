.. _com:

Communication Abstraction
==========================

This library contains a generic communication abstraction specifically targeted
towards the exchange of binary data like CCSDS packets.

The core of this abstraction is the :py:class:`tmtccmd.com.ComInterface` class.
An implementation of this class can be passed to other library components and makes
the commanding logic independent of the used interface. It is also possible to
use this abstraction independenctly of the other library components and implement
custom interfaces.

The use of a communication abstraction allows to use the same TMTC specification
independently of the used communication interface. For example, it might be possible to build
an on-board software both for a remote MCU and for a hosted system. The MCU might expect the
same command data to be exchanged via a specific transport layer, while the hosted version
might just use a UDP socket.

The following example shows how to use the :py:class:`tmtccmd.com.udp.UdpComIF` to send
PUS packets (a subtype of CCSDS space packets) to a UDP server

.. testcode:: udp_com

    import socket

    from tmtccmd.com import ComInterface
    from tmtccmd.com.udp import UdpComIF, EthAddr
    from spacepackets.ecss.tc import PusTelecommand

    def send_my_telecommand(tc: PusTelecommand, com_if: ComInterface):
    	com_if.send(tc.pack())

    simulated_udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = ("127.0.0.1", 60000)
    simulated_udp_server.bind(addr)

    udp_client = UdpComIF("udp", send_address=EthAddr.from_tuple(addr))
    udp_client.initialize()
    udp_client.open()

    ping_tc = PusTelecommand(service=17, subservice=1, apid=0x020)
    send_my_telecommand(ping_tc, udp_client)

    recvd_data, sender_addr = simulated_udp_server.recvfrom(4096)
    recvd_tc = PusTelecommand.unpack(recvd_data)

    print(f"Sent TC: {ping_tc}")
    print(f"Received TC: {recvd_tc}")
    udp_client.close()

Output:

.. testoutput:: udp_com

    Sent TC: PUS TC[17, 1] with Request ID 0x1820c000, APID 0x020, SSC 0
    Received TC: PUS TC[17, 1] with Request ID 0x1820c000, APID 0x020, SSC 0

Here is another example where a the same packet is sent via a serial interface. This
example only runs of Unix systems because it simulates a serial port using
`pty <https://docs.python.org/3/library/pty.html>`_.

.. testcode:: serial_cobs
    # Unfortunately, this does not work..
    # :skipif: is_win

    import os
    import pty
    import time

    from tmtccmd.com import ComInterface
    from spacepackets.ecss.tc import PusTelecommand

    def send_my_telecommand(tc: PusTelecommand, com_if: ComInterface):
    	com_if.send(tc.pack())

    simulated_ser_device, pty_slave = pty.openpty()
    simulated_serial_port = os.ttyname(pty_slave)
    ser_cfg = SerialCfg("serial_cobs", serial_port=slave_name, baud_rate=9600, serial_timeout=1.0)
    cobs_com_if = SerialCobsComIF(ser_cfg)
    cobs_com_if.initialize()
    cobs_com_if.open()

    test_data = bytes([0x01, 0x02, 0x03])
    # Will be used later and to determine how much to read.
    encoded_data = cobs.encode(test_data)

    # Data will be COBS encoded internally, with the 0 frame delimiter inserted at the start and
    # end
    cobs_com_if.send(test_data)

    # Other side receives COBS encoded packet
    encoded_packet = os.read(simulated_ser_device, len(encoded_data) + 2)
    print(encoded_packet.hex(sep=','))
    decoded_packet = cobs.decode(encoded_packet[1:-1])
    print(f"Encoded packet received at simulated serial device: {encoded_packet.hex(sep=',')}")
    print(f"Decoded packet: {decoded_packet.hex(sep=',')}")

    # Now send COBS encoded data back
    data_sent_back = bytes([0x01, 0x02, 0x03])
    # 0 start marker
    cobs_encoded_data = bytearray([0])
    cobs_encoded_data.extend(encoded_data)
    # 0 end marker
    cobs_encoded_data.append(0)
    os.write(simulated_ser_device, cobs_encoded_data)
    # Receiver thread might take some time
    time.sleep(0.1)

    packet_list = cobs_com_if.receive()
    print(f"Data received from simulated serial device: {packet_list[0].hex(sep=',')}")
