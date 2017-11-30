import sys
import threading
import os
import signal
import argparse
import random
import subprocess

from multiprocessing import Process

def signal_handler(siganl, frames):
    print("Killing the running services.")
    for process in processes:
        print("Killing process {}".format(process.pid))
        os.system("kill -9 {}".format(process.pid))
    sys.exit(0)

def services(device_name=None):
    from topology.graph.graph_service import graph_service
    from topology.sniffer.sniffing_service import sniffing_service
    from database.database_service import database_service

    global processes
    processes = [
        Process(target=database_service),
        Process(target=graph_service)
    ]

    if device_name is not None:
        processes.append(Process(target=sniffing_service, args=(device_name,)))
    else:
        processes.append(Process(target=sniffing_service))

    for process in processes:
        process.start()

def set_ports(node_type):
    import service.server as config_keeper

    port_offset = 30000

    if node_type == "slave":
        config = {
            'database' : port_offset + random.randint(0, port_offset),
            'sniffer' : port_offset + random.randint(0, port_offset),
            'graph' : port_offset + random.randint(0, port_offset)
        }
    elif node_type == "master":
        config = {
            'database' : 29000,
            'sniffer' : 29001,
            'graph' : 29002
        }
    else:
        print("Wrong type specified.")
        os.kill(os.getpid(), signal.SIGINT)

    setattr(config_keeper, 'config', config)

if __name__ == "__main__":
    if os.getuid() != 0:
        print("Must be run as root.")
        exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("type", type=str,
        help="The type of node run: master or slave")
    parser.add_argument("-m", "--master", type=str, default=None,
        help="Specify master IP for connecting a slave.")
    parser.add_argument("-p", "--port", type=str, default=None,
        help="Specify port for runnning a slave.")
    parser.add_argument("-i", "--interface", type=str, default=None,
        help="The network interface listened to.")

    args = parser.parse_args()
    set_ports(args.type)

    if args.interface is None:
        services()
    else:
        services(args.interface)
    signal.signal(signal.SIGINT, signal_handler)

    if args.type == "master":
        master_proc = subprocess.Popen(['python3', 'dissemination/master.py'], shell=False)
        processes.append(master_proc)

    if args.type == "slave":
        master_ip = args.master
        port      = args.port

        if master_ip is None or port is None:
            print("Not enough arguments provided for slave mode.")
            os.kill(os.getpid(), signal.SIGINT)

        slave_proc = subprocess.Popen(['python3', 'dissemination/slave.py', master_ip, port],  shell=False)
        processes.append(master_proc)
