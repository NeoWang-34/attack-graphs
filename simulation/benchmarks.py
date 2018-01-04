from __future__ import absolute_import

import sys
import os
import subprocess
import time
import signal
import psutil
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import matplotlib.pyplot as plt
from service.server import config
from topology.graph.graph import Graph
from topology.graph.graph import Node
from service.client import LocalClient
from random import randint, random, shuffle
from dissemination.util import get_host_ip

from math import exp

ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
app = os.path.join(ROOT, "service.py")
processes = []

def get_path(benchmark):
    PATH = os.path.dirname(os.path.realpath(__file__))
    PATH = os.path.join(PATH, "confs")
    PATH = os.path.join(PATH, "{}.json".format(benchmark))
    return PATH

def clear_processes():
    this_proc = os.getpid()
    for proc in psutil.process_iter():
        procd = proc.as_dict(attrs=['pid', 'name'])
        if "python" in str(procd['name']) and procd['pid'] != this_proc:
            proc.kill()

def add_process(command):
    global processes

    print("> {}".format(command))
    slave_proc = subprocess.Popen(command.split(" "),  shell=False)
    processes.append(slave_proc)

def generate_graph(nodes, max_edges):
    graph = Graph()

    def int_to_ip(value):
        a = (value >> 24) & 255
        b = (value >> 16) & 255
        c = (value >> 8) & 255
        d = (value >> 0) & 255
        return "{}.{}.{}.{}".format(a, b, c, d)

    nodes = [Node(int_to_ip(i)) for i in range(0, nodes)]
    for n in nodes:
        n.running = {
            "scanned" : "false",
            "Host": {
              "os" : "ACER RT-N56U WAP (Linux 3.2)",
              "ip" : n.ip,
              "RunningServices": []
          }
        }

    edges = [(n1, n2) for n1 in nodes for n2 in nodes]
    shuffle(edges)

    for n1, n2 in edges:
        if max_edges == 0:
            break
        before = len(graph.edges)
        graph.add_edge(n1, n2)
        if len(graph.edges) > before:
            max_edges -= 1
    return graph

def export_graph(graph, benchmark):
    os.system("touch {}".format(get_path(benchmark)))
    with open(get_path(benchmark), "w") as config:
        config.write(str(graph.to_json()))

def delete_simulation_config(benchmark):
    os.remove(get_path(benchmark))

def create_master(benchmark):
    add_process("sudo python3 {} master -s {}.json".format(app, benchmark))

def create_slave(benchmark, port):
    add_process("sudo python3 {} slave -m {} -p {} -s {}.json".format(app, get_host_ip(), port, benchmark))

def take_snapshot():
    t = time.clock()
    try:
        graph = LocalClient(config["graph"]).get("/graph")
        graph = Graph.from_json(graph)
        return t, graph
    except Exception as e:
        return None

def process_snapshots(snapshots, processor):
    return [processor(t, s) for t, s in snapshots]

def build_scenario(name, nodes, edges, slaves, snaps, pause, processor):
    graph = generate_graph(nodes, edges)
    export_graph(graph, name)

    create_master(name)
    for i in range(slaves):
        time.sleep(2)
        create_slave(name, 1000 + i)

    snapshots = [(time.clock(), graph)]
    for i in range(0, snaps):
        time.sleep(pause)
        snapshot = take_snapshot()
        if snapshot is not None:
            snapshots.append(snapshot)
    delete_simulation_config(name)
    nodes = process_snapshots(snapshots, processor)

    clear_processes()
    return nodes

def nbr_service(graph):
    return len(graph.populated)

def plot(file_name, all_stats, label, selector):
    s = 0
    for line in all_stats:
        plt.plot([selector(entry) for entry in line][1:], label="{} slaves".format(s))
        s += 1
    plt.xlabel('time')
    plt.ylabel(label)
    plt.grid(True)
    plt.legend()

    plt.savefig(os.path.join(ROOT, "simulation", "res", file_name))
    plt.gcf().clear()

def scenario_stats(name, nodes, edges, snaps, pause):
    all_stats = []
    for slaves in [0, 1, 2]:
        all_stats.append(build_scenario(
            name=name,
            nodes=nodes,
            edges=edges,
            slaves=slaves,
            snaps=snaps,
            pause=pause,
            processor=lambda t, graph: (t, len(graph.nodes), len(graph.edges), nbr_service(graph))
        ))

    plot(file_name="{}_hosts.png".format(name), all_stats=all_stats, label="hosts detected", selector=lambda x: x[1])
    plot(file_name="{}_edges.png".format(name), all_stats=all_stats, label="edges detected", selector=lambda x: x[2])
    plot(file_name="{}_scanned.png".format(name), all_stats=all_stats, label="scanned hosts", selector=lambda x: x[3])

if __name__ == "__main__":
    scenario_stats("small", 20, 210, 30, 1)
    scenario_stats("medium1", 100, 10000, 20, 3)
    scenario_stats("medium2", 300, 50000, 20, 3)
    scenario_stats("sparse", 1000, 10000, 20, 3)
