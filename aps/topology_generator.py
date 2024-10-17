import json

import argparse

import networkx as nx


topo_base = {
    "p4_src": "p4src/hula.p4",
    "cli": True,
    "pcap_dump": True,
    "enable_log": True,
    "switch_node": {
        "module_name": "p4utils.mininetlib.node",
        "object_name": "P4RuntimeSwitch",
    },
    "compiler_module": {"options": {"p4rt": True}},
    "topology": {"assignment_strategy": "l3"},
}


def create_fat_tree_topo(k):

    topo_base["topology"]["links"] = []

    # Total number of switches

    num_pods = k

    num_core_switches = (k // 2) ** 2

    num_agg_switches = num_pods * (k // 2)

    num_edge_switches = num_pods * (k // 2)

    # Total number of hosts

    num_hosts = num_pods * (k // 2) ** 2

    # Hosts

    topo_base["topology"]["hosts"] = {f"h{i}": {} for i in range(1, num_hosts + 1)}

    # Switches

    switches = {}

    for i in range(1, num_core_switches + 1):

        switches[f"core{i}"] = {}

    for i in range(1, num_agg_switches + 1):

        switches[f"agg{i}"] = {}

    for i in range(1, num_edge_switches + 1):

        switches[f"edge{i}"] = {}

    topo_base["topology"]["switches"] = switches

    # Connect hosts to edge switches

    host_id = 1

    for pod in range(num_pods):

        for edge in range(k // 2):

            edge_switch_id = pod * (k // 2) + edge + 1

            for h in range(k // 2):

                topo_base["topology"]["links"].append(
                    [f"h{host_id}", f"edge{edge_switch_id}"]
                )

                host_id += 1

    # Connect edge switches to aggregation switches

    for pod in range(num_pods):

        for edge in range(k // 2):

            edge_switch_id = pod * (k // 2) + edge + 1

            for agg in range(k // 2):

                agg_switch_id = pod * (k // 2) + agg + 1

                topo_base["topology"]["links"].append(
                    [f"edge{edge_switch_id}", f"agg{agg_switch_id}"]
                )

    # Connect aggregation switches to core switches

    for pod in range(num_pods):

        for agg in range(k // 2):

            agg_switch_id = pod * (k // 2) + agg + 1

            for core in range(k // 2):

                core_switch_id = core * (k // 2) + agg + 1

                topo_base["topology"]["links"].append(
                    [f"agg{agg_switch_id}", f"core{core_switch_id}"]
                )


def create_linear_topo(num_switches):

    topo_base["topology"]["links"] = []

    # Connect hosts with switches

    for i in range(1, num_switches + 1):

        topo_base["topology"]["links"].append(["h{}".format(i), "s{0}".format(i)])

    # Connect switches

    for i in range(1, num_switches):

        topo_base["topology"]["links"].append(["s{}".format(i), "s{}".format(i + 1)])

    topo_base["topology"]["hosts"] = {
        "h{0}".format(i): {} for i in range(1, num_switches + 1)
    }

    topo_base["topology"]["switches"] = {
        "s{0}".format(i): {} for i in range(1, num_switches + 1)
    }


def create_circular_topo(num_switches):

    create_linear_topo(num_switches)

    # Add link between s1 and sN

    topo_base["topology"]["links"].append(["s{}".format(1), "s{}".format(num_switches)])


def create_random_topo(degree=4, num_switches=10):

    topo_base["topology"]["links"] = []

    g = nx.random_regular_graph(degree, num_switches)

    trials = 0

    while not nx.is_connected(g):

        g = nx.random_regular_graph(degree, num_switches)

        trials += 1

        if trials >= 10:

            print("Could not create a connected graph")

            return

    # Connect hosts with switches

    for i in range(1, num_switches + 1):

        topo_base["topology"]["links"].append(["h{}".format(i), "s{0}".format(i)])

    for edge in g.edges:

        topo_base["topology"]["links"].append(
            ["s{}".format(edge[0] + 1), "s{}".format(edge[1] + 1)]
        )

    topo_base["topology"]["hosts"] = {
        "h{0}".format(i): {} for i in range(1, num_switches + 1)
    }

    topo_base["topology"]["switches"] = {
        "s{0}".format(i): {} for i in range(1, num_switches + 1)
    }


def main():

    pass


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output_name", type=str, required=False, default="p4app_test.json"
    )

    parser.add_argument("--topo", type=str, default="linear")

    parser.add_argument("-k", type=int, required=False, default=4)

    parser.add_argument("-n", type=int, required=False, default=2)

    parser.add_argument("-d", type=int, required=False, default=4)

    args = parser.parse_args()

    if args.topo == "linear":

        create_linear_topo(args.n)

    elif args.topo == "circular":

        create_circular_topo(args.n)

    elif args.topo == "random":

        create_random_topo(args.d, args.n)

    elif args.topo == "fattree":

        create_fat_tree_topo(args.k)

    json.dump(topo_base, open(args.output_name, "w"), sort_keys=True, indent=2)
