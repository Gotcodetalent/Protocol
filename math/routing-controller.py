import os
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_p4runtime_API import SimpleSwitchP4RuntimeAPI
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI


class RoutingController:
    def __init__(self):
        if not os.path.exists("topology.json"):
            print("Could not find topology object!!!\n")
            raise Exception
        self.topo = load_topo("topology.json")
        self.controllers = {}
        self.init()

    def init(self):
        self.connect_to_switches()
        self.reset_states()
        self.set_table_defaults()
        self.setup_multicast_groups()
        self.setup_hula_nhop()
        self.setup_dst_tor_table()
        self.setup_edge_forward()

    def reset_states(self):
        """Resets registers, tables, etc."""
        for p4rtswitch, controller in self.controllers.items():
            controller.reset_state()
            thrift_port = self.topo.get_thrift_port(p4rtswitch)
            controller_thrift = SimpleSwitchThriftAPI(thrift_port)
            controller_thrift.reset_state()

    def connect_to_switches(self):
        for p4rtswitch, data in self.topo.get_p4switches().items():
            device_id = self.topo.get_p4switch_id(p4rtswitch)
            grpc_port = self.topo.get_grpc_port(p4rtswitch)
            p4rt_path = data["p4rt_path"]
            json_path = data["json_path"]
            self.controllers[p4rtswitch] = SimpleSwitchP4RuntimeAPI(
                device_id, grpc_port, p4rt_path=p4rt_path, json_path=json_path
            )

    def set_table_defaults(self):
        for controller in self.controllers.values():
            controller.table_set_default("ipv4_lpm", "drop", [])
            controller.table_set_default("ecmp_group_to_nhop", "drop", [])

    def setup_multicast_groups(self):
        """Sets up multicast groups for edge and intermediate switches"""
        for sw_name, controller in self.controllers.items():
            if sw_name in ["s1", "s6"]:
                self.setup_edge_multicast_group(sw_name, controller)
            else:
                self.setup_intermediate_multicast_group(sw_name, controller)

    def setup_edge_multicast_group(self, sw_name, controller):
        interfaces_to_port = self.topo.get_node_intfs(fields=["port"])[sw_name].copy()
        interfaces_to_port.pop("lo", None)
        interfaces_to_port.pop(self.topo.get_cpu_port_intf(sw_name), None)
        dst_tor_ids = ["1", "6"]  # s1 和 s6 的 ID
        for ingress_port in interfaces_to_port.values():
            port_list = list(interfaces_to_port.values())
            del port_list[port_list.index(ingress_port)]
            upstream_ports = []
            for port in interfaces_to_port.values():
                try:
                    connected_node = self.topo.port_to_node(sw_name, port)
                    if connected_node in ["s2", "s3", "s4", "s5"]:
                        upstream_ports.append(port)
                except Exception as e:
                    print(f"Error processing port {port} on switch {sw_name}: {e}")
            # 如果封包來自中繼節點 (s2~s5)，則不群播
            if ingress_port in upstream_ports:
                print(
                    f"Skipping multicast for switch {sw_name} on ingress port {ingress_port} from upstream node"
                )
                continue
            if upstream_ports:
                for dst_tor in dst_tor_ids:
                    print(
                        f"Creating multicast group on switch {sw_name} with ports {upstream_ports} for ingress_port {ingress_port} and dst_tor {dst_tor}"
                    )
                    controller.mc_mgrp_create(ingress_port, upstream_ports)
                    controller.table_add(
                        "set_mcast",
                        "set_probe_mcast",
                        [str(ingress_port), dst_tor],
                        [str(ingress_port)],
                    )
            else:
                print(
                    f"No upstream ports for switch {sw_name} on ingress port {ingress_port}"
                )

    def setup_intermediate_multicast_group(self, sw_name, controller):
        interfaces_to_port = self.topo.get_node_intfs(fields=["port"])[sw_name].copy()
        interfaces_to_port.pop("lo", None)
        interfaces_to_port.pop(self.topo.get_cpu_port_intf(sw_name), None)
        for ingress_port in interfaces_to_port.values():
            for dst_tor in ["1", "6"]:
                port_list = list(interfaces_to_port.values())
                if ingress_port in port_list:
                    port_list.remove(
                        ingress_port
                    )  # Remove ingress port to avoid loopback
                tor_switch_name = f"s{dst_tor}"
                for port in port_list.copy():
                    connected_node = self.topo.port_to_node(sw_name, port)
                    if connected_node == tor_switch_name:
                        port_list.remove(
                            port
                        )  # Remove the port connected to the `dst_tor`
                mcast_ports = port_list
                if mcast_ports:
                    group_id = (ingress_port << 8) | int(dst_tor)
                    print(
                        f"Creating multicast group {group_id} on switch {sw_name} with ports {mcast_ports}"
                    )
                    controller.mc_mgrp_create(group_id, mcast_ports)
                    controller.table_add(
                        "set_mcast",
                        "set_probe_mcast",
                        [str(ingress_port), dst_tor],
                        [str(group_id)],
                    )
                else:
                    print(
                        f"No multicast ports for switch {sw_name} on ingress port {ingress_port} with dst_tor {dst_tor}"
                    )

    def setup_hula_nhop(self):
        """Sets up Hula NHOP table entries for all switches"""
        for sw_name, controller in self.controllers.items():
            for intf, port in self.topo.get_node_intfs(fields=["port"])[
                sw_name
            ].items():
                if "cpu" not in intf and "lo" not in intf:
                    try:
                        port_number = int(port)
                        connected_node = self.topo.port_to_node(sw_name, port)
                        connected_mac = self.topo.node_to_node_mac(
                            sw_name, connected_node
                        )
                        print(
                            f"Adding entry to hula_set_nhop at {sw_name}: port {port_number} -> {connected_mac}"
                        )
                        controller.table_add(
                            "hula_set_nhop",
                            "hula_nhop",
                            [str(port_number)],
                            [connected_mac],
                        )
                    except Exception as e:
                        print(
                            f"Error setting hula_nhop for {sw_name}, port {port}: {e}"
                        )

    def setup_dst_tor_table(self):
        """Sets up get_dst_tor table entries for all switches"""
        for sw_name, controller in self.controllers.items():
            self_id = int(sw_name[1:])  # Correctly set self_id to switch number
            for host in self.topo.get_hosts():
                host_ip = self.topo.get_host_ip(host)
                connected_edges = self.topo.get_switches_connected_to(host)
                if connected_edges:
                    edge_switch = connected_edges[0]
                    tor_id = int(edge_switch[1:])
                    print(
                        f"Adding entry to get_dst_tor at {sw_name}: IP {host_ip} -> TOR {tor_id}, Self {self_id}"
                    )
                    controller.table_add(
                        "get_dst_tor",
                        "set_dst_tor",
                        [str(host_ip)],
                        [str(tor_id), str(self_id)],
                    )
                else:
                    print(f"Host {host} is not connected to any edge switch.")

    def setup_edge_forward(self):
        """Sets up edge_forward table entries for edge switches"""
        for sw_name, controller in self.controllers.items():
            if sw_name in ["s1", "s6"]:
                for host in self.topo.get_hosts_connected_to(sw_name):
                    host_ip = self.topo.get_host_ip(host)
                    host_mac = self.topo.get_host_mac(host)
                    sw_port = self.topo.node_to_node_port_num(sw_name, host)
                    print(
                        f"Adding entry to edge_forward at {sw_name}: IP {host_ip} -> MAC {host_mac}, Port {sw_port}"
                    )
                    controller.table_add(
                        "edge_forward",
                        "simple_forward",
                        [host_ip],
                        [host_mac, str(sw_port)],
                    )

    def route(self):
        switch_ecmp_groups = {
            sw_name: {} for sw_name in self.topo.get_p4switches().keys()
        }
        for sw_name, controller in self.controllers.items():
            for sw_dst in self.topo.get_p4switches():
                if sw_name == sw_dst:
                    for host in self.topo.get_hosts_connected_to(sw_name):
                        sw_port = self.topo.node_to_node_port_num(sw_name, host)
                        host_ip = self.topo.get_host_ip(host) + "/32"
                        host_mac = self.topo.get_host_mac(host)
                        print("table_add at {}:".format(sw_name))
                        self.controllers[sw_name].table_add(
                            "ipv4_lpm",
                            "set_nhop",
                            [str(host_ip)],
                            [str(host_mac), str(sw_port)],
                        )
                else:
                    if self.topo.get_hosts_connected_to(sw_dst):
                        paths = self.topo.get_shortest_paths_between_nodes(
                            sw_name, sw_dst
                        )
                        for host in self.topo.get_hosts_connected_to(sw_dst):
                            if len(paths) == 1:
                                next_hop = paths[0][1]
                                host_ip = self.topo.get_host_ip(host) + "/24"
                                sw_port = self.topo.node_to_node_port_num(
                                    sw_name, next_hop
                                )
                                dst_sw_mac = self.topo.node_to_node_mac(
                                    next_hop, sw_name
                                )
                                print("table_add at {}:".format(sw_name))
                                self.controllers[sw_name].table_add(
                                    "ipv4_lpm",
                                    "set_nhop",
                                    [str(host_ip)],
                                    [str(dst_sw_mac), str(sw_port)],
                                )
                            elif len(paths) > 1:
                                next_hops = [x[1] for x in paths]
                                dst_macs_ports = [
                                    (
                                        self.topo.node_to_node_mac(next_hop, sw_name),
                                        self.topo.node_to_node_port_num(
                                            sw_name, next_hop
                                        ),
                                    )
                                    for next_hop in next_hops
                                ]
                                host_ip = self.topo.get_host_ip(host) + "/24"
                                if switch_ecmp_groups[sw_name].get(
                                    tuple(dst_macs_ports), None
                                ):
                                    ecmp_group_id = switch_ecmp_groups[sw_name].get(
                                        tuple(dst_macs_ports), None
                                    )
                                    print("table_add at {}:".format(sw_name))
                                    self.controllers[sw_name].table_add(
                                        "ipv4_lpm",
                                        "ecmp_group",
                                        [str(host_ip)],
                                        [str(ecmp_group_id), str(len(dst_macs_ports))],
                                    )
                                else:
                                    new_ecmp_group_id = (
                                        len(switch_ecmp_groups[sw_name]) + 1
                                    )
                                    switch_ecmp_groups[sw_name][
                                        tuple(dst_macs_ports)
                                    ] = new_ecmp_group_id
                                    for i, (mac, port) in enumerate(dst_macs_ports):
                                        print("table_add at {}:".format(sw_name))
                                        self.controllers[sw_name].table_add(
                                            "ecmp_group_to_nhop",
                                            "set_nhop",
                                            [str(new_ecmp_group_id), str(i)],
                                            [str(mac), str(port)],
                                        )
                                    print("table_add at {}:".format(sw_name))
                                    self.controllers[sw_name].table_add(
                                        "ipv4_lpm",
                                        "ecmp_group",
                                        [str(host_ip)],
                                        [
                                            str(new_ecmp_group_id),
                                            str(len(dst_macs_ports)),
                                        ],
                                    )

    def main(self):
        self.route()


if __name__ == "__main__":
    controller = RoutingController().main()
