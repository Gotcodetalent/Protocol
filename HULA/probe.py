import argparse

import sys

import socket

import random

import struct

import time

from scapy.all import sendp, get_if_list, get_if_hwaddr, bind_layers

from scapy.all import Packet, BitField, Raw

from scapy.all import Ether, IP


def get_if():

    ifs = get_if_list()

    iface = None

    for i in get_if_list():

        if "eth0" in i:

            iface = i

            break

    if not iface:

        print("Cannot find eth0 interface")

        exit(1)

    return iface


class Hula(Packet):

    fields_desc = [
        BitField("dst_tor", 0, 24),
        BitField("path_util", 0, 8),
        BitField("var", 0, 8),
        BitField("ttl", 0, 8),  # Set initial TTL value to 16
    ]


bind_layers(IP, Hula, proto=0x42)


def main():

    iface = get_if()

    hw_if = get_if_hwaddr(iface)

    print("sending probe on interface %s." % (iface))

    pkt = Ether(src=hw_if, dst="ff:ff:ff:ff:ff:ff")

    pkt = pkt / IP(dst="224.0.0.1", proto=66)

    # Map host to its corresponding edge switch ID

    host_to_edge = {
        "h1": 1,
        "h2": 1,
        "h3": 2,
        "h4": 2,
        "h5": 3,
        "h6": 3,
        "h7": 4,
        "h8": 4,
        "h9": 5,
        "h10": 5,
        "h11": 6,
        "h12": 6,
        "h13": 7,
        "h14": 7,
        "h15": 8,
        "h16": 8,
    }

    # Extract host ID from the interface name (e.g., h1-eth0 -> h1)

    host_id = iface.split("-")[0]

    # Get the corresponding edge switch ID

    dst_tor = host_to_edge.get(host_id, 0)  # Default to 0 if not found

    pkt = pkt / Hula(
        dst_tor=dst_tor, path_util=256, ttl=64
    )  # Include the TTL field in the packet

    pkt = pkt / Raw("probe packet")

    # Keep sending probes

    while True:

        sendp(pkt, iface=iface, verbose=False)

        time.sleep(
            random.uniform(1, 1)
        )  # Random sleep interval between 1 and 2 seconds


if __name__ == "__main__":

    main()
