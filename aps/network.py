from p4utils.mininetlib.network_API import NetworkAPI


net = NetworkAPI()


# Network general options

net.setLogLevel("info")

net.setCompiler(p4rt=True)


# Network definition

# Edge switches

for i in range(1, 9):

    net.addP4RuntimeSwitch(f"edge{i}")


# Aggregation switches

for i in range(1, 9):

    net.addP4RuntimeSwitch(f"agg{i}")


# Core switches

for i in range(1, 5):

    net.addP4RuntimeSwitch(f"core{i}")


net.setP4SourceAll("p4src/hula.p4")


# Hosts

for i in range(1, 17):

    net.addHost(f"h{i}")


# Links between hosts and edge switches

for i in range(1, 9):

    net.addLink(f"h{2*i-1}", f"edge{i}")

    net.addLink(f"h{2*i}", f"edge{i}")


# Links between edge and aggregation switches

for i in range(1, 5):

    net.addLink(f"edge{i}", "agg1")

    net.addLink(f"edge{i}", "agg2")

    net.addLink(f"edge{i+4}", "agg3")

    net.addLink(f"edge{i+4}", "agg4")


for i in range(1, 5):

    net.addLink(f"edge{i}", "agg5")

    net.addLink(f"edge{i}", "agg6")

    net.addLink(f"edge{i+4}", "agg7")

    net.addLink(f"edge{i+4}", "agg8")


# Links between aggregation and core switches

for i in range(1, 5):

    net.addLink(f"agg{i}", "core1")

    net.addLink(f"agg{i}", "core2")

    net.addLink(f"agg{i+4}", "core3")

    net.addLink(f"agg{i+4}", "core4")


# Assignment strategy

net.l3()


# Nodes general options

net.enablePcapDumpAll()

net.enableLogAll()

net.enableCli()

net.startNetwork()
