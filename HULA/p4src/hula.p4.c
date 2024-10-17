/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>
// My includes
#include "include/headers.p4"
#include "include/parsers.p4"
#define REGISTER_SIZE 8192
#define TIMESTAMP_WIDTH 48
#define ID_WIDTH 16
#define FLOWLET_TIMEOUT 48w500
#define REDUNDANCY_TIME_WINDOW 48w500
#define DEFAULT_PROBE_TTL 16
#define NUM_PORTS 4
#define NUM_TORS 9
#define NUM_HOSTS 16
typedef bit<8> util_t;
typedef bit<48> time_t;
typedef bit<9> port_id_t;
const util_t PROBE_FREQ_FACTOR = 6;
/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/
control MyVerifyChecksum(inout headers hdr, inout metadata meta)
{
    apply {}
}
/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/
control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata)
{
    register<util_t>((bit<32>)NUM_TORS) port_util;
    register<time_t>((bit<32>)NUM_TORS) dsttor_last_updated;
    register<time_t>((bit<32>)NUM_TORS) update_time;
    register<port_id_t>((bit<32>)NUM_TORS) best_hop;
    register<util_t>((bit<32>)NUM_TORS) min_path_util;
    register<time_t>((bit<32>)1024) flowlet_time;
    register<port_id_t>((bit<32>)1024) flowlet_hop;
    register<bit<32>>((bit<32>)1024) flowlet_size;
    register<bit<ID_WIDTH>>(REGISTER_SIZE) flowlet_to_id;
    register<bit<TIMESTAMP_WIDTH>>(REGISTER_SIZE) flowlet_time_stamp;
    action drop()
    {
        mark_to_drop(standard_metadata);
    }
    action set_probe_mcast(bit<16> mcast_grp)
    {
        // ensure probe do not cause loops
        standard_metadata.mcast_grp = mcast_grp;
        hdr.probe.ttl = hdr.probe.ttl - 1;
    }
    action probe_handle_probe()
    {
        bit<48> curr_time = standard_metadata.ingress_global_timestamp;
        bit<32> dst_tor = (bit<32>)hdr.probe.dst_tor;
        bit<8> tx_util;
        bit<8> mpu;
        bit<48> up_time;
        port_util.read(tx_util, (bit<32>)standard_metadata.ingress_port);
        min_path_util.read(mpu, dst_tor);
        update_time.read(up_time, dst_tor);
        if (hdr.probe.path_util < tx_util)
        {
            hdr.probe.path_util = tx_util;
        }
        bool cond = (hdr.probe.path_util < mpu || curr_time - up_time > FLOWLET_TIMEOUT);
        mpu = cond ? hdr.probe.path_util : mpu;
        min_path_util.write(dst_tor, mpu);
        up_time = cond ? curr_time : up_time;
        update_time.write(dst_tor, up_time);
        port_id_t bh_temp;
        best_hop.read(bh_temp, dst_tor);
        bh_temp = cond ? standard_metadata.ingress_port : bh_temp;
        best_hop.write(dst_tor, bh_temp);
        min_path_util.read(mpu, dst_tor);
        hdr.probe.path_util = mpu;
    }
    action probe_handle_data_packet()
    {
        bit<48> curr_time = standard_metadata.ingress_global_timestamp;
        bit<8> tx_util;
        port_util.read(tx_util, (bit<32>)standard_metadata.ingress_port);
        bit<32> flow_hash;
        bit<48> flow_t;
        port_id_t flow_h;
        port_id_t best_h;
        hash(flow_hash, HashAlgorithm.csum16, 32w0, {
                                                        hdr.ipv4.srcAddr,
                                                        hdr.ipv4.dstAddr,
                                                        hdr.ipv4.protocol,
                                                        hdr.tcp.srcPort,
                                                        hdr.tcp.dstPort,
                                                    },
             32w1024);
        flowlet_time.read(flow_t, flow_hash);
        best_hop.read(best_h, meta.dst_tor);
        port_id_t tmp;
        flowlet_hop.read(tmp, flow_hash);
        tmp = (curr_time - flow_t > FLOWLET_TIMEOUT) ? best_h : tmp;
        flowlet_hop.write(flow_hash, tmp);
        flowlet_hop.read(flow_h, flow_hash);
        standard_metadata.egress_spec = flow_h;
        flowlet_time.write(flow_hash, curr_time);
    }
    action read_flowlet_registers()
    {
        hash(meta.flowlet_register_index, HashAlgorithm.crc16,
             (bit<16>)0,
             {hdr.ipv4.srcAddr, hdr.ipv4.dstAddr, hdr.tcp.srcPort, hdr.tcp.dstPort, hdr.ipv4.protocol},
             (bit<14>)8192);
        flowlet_time_stamp.read(meta.flowlet_last_stamp, (bit<32>)meta.flowlet_register_index);
        flowlet_to_id.read(meta.flowlet_id, (bit<32>)meta.flowlet_register_index);
        flowlet_time_stamp.write((bit<32>)meta.flowlet_register_index, standard_metadata.ingress_global_timestamp);
    }
    action update_flowlet_id()
    {
        bit<32> random_t;
        random(random_t, (bit<32>)0, (bit<32>)65000);
        meta.flowlet_id = (bit<16>)random_t;
        flowlet_to_id.write((bit<32>)meta.flowlet_register_index, (bit<16>)meta.flowlet_id);
    }
    action ecmp_group(bit<14> ecmp_group_id, bit<16> num_nhops)
    {
        bool cond = meta.random_path == 1;
        bit<48> curr_time = standard_metadata.ingress_global_timestamp;
        hash(meta.ecmp_hash,
             HashAlgorithm.crc16,
             (bit<1>)0,
             {hdr.ipv4.srcAddr, hdr.ipv4.dstAddr, hdr.tcp.srcPort, hdr.tcp.dstPort, hdr.ipv4.protocol},
             num_nhops);

        meta.ecmp_group_id = ecmp_group_id;
    }
    action set_nhop(macAddr_t dstAddr, egressSpec_t port)
    {
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
        standard_metadata.egress_spec = port;
    }
    action hula_nhop(macAddr_t dstAddr)
    {
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }
    action set_dst_tor(tor_id_t dst_tor, tor_id_t self_id)
    {
        meta.dst_tor = (bit<32>)dst_tor;
        meta.self_id = (bit<32>)self_id;
    }
    // Used when matching a probe packet.
    action dummy_dst_tor()
    {
        meta.dst_tor = 0;
        meta.self_id = 1;
    }
    action simple_forward(macAddr_t dstAddr, egressSpec_t port)
    {
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        standard_metadata.egress_spec = port;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }
    table edge_forward
    {
        key = {
            hdr.ipv4.dstAddr : exact;
    }
    actions = {
        simple_forward;
}
size = NUM_HOSTS;
}
table get_dst_tor
{
    key = {
        hdr.ipv4.dstAddr : exact;
}
actions = {
    set_dst_tor;
dummy_dst_tor;
}
default_action = dummy_dst_tor;
}
table hula_set_nhop
{
    key = {
        standard_metadata.egress_spec : exact;
}
actions = {
    hula_nhop;
drop;
}
size = 1024;
default_action = drop();
}
table set_mcast
{
    key = {
        standard_metadata.ingress_port : exact;
}
actions = {
    set_probe_mcast;
}
size = 1024;
}
table ecmp_group_to_nhop
{
    key = {
        meta.ecmp_group_id : exact;
    meta.ecmp_hash : exact;
}
actions = {
    drop;
set_nhop;
}
size = 1024;
}
table ipv4_lpm
{
    key = {
        hdr.ipv4.dstAddr : lpm;
}
actions = {
    set_nhop;
ecmp_group;
drop;
}
size = 1024;
default_action = drop;
}
action update_ingress_statistics()
{
    time_t last_update;
    time_t curr_time = standard_metadata.ingress_global_timestamp;
    util_t util;
    dsttor_last_updated.read(last_update, meta.dst_tor);
    bool condition = (curr_time - last_update > REDUNDANCY_TIME_WINDOW);
    meta.redundancy = condition ? 1w1 : 1w0;
    dsttor_last_updated.write(meta.dst_tor, curr_time);
    bit<32> port = (bit<32>)standard_metadata.ingress_port;
    port_util.read(util, port);
    bit<8> delta_t = (bit<8>)(curr_time - last_update);
    util = (((bit<8>)standard_metadata.packet_length + util) << PROBE_FREQ_FACTOR) - delta_t;
    util = util >> PROBE_FREQ_FACTOR;
    port_util.write(port, util);
}
apply
{
    get_dst_tor.apply();
    update_ingress_statistics();
    if (hdr.ipv4.isValid())
    {
        if (hdr.probe.isValid())
        {
            if (meta.redundancy == 0)
            {
                drop();
            }
            else
            {
                @atomic
                {
                    probe_handle_probe();
                }
                set_mcast.apply();
            }
        }
        else
        {
            @atomic
            {
                read_flowlet_registers();
                meta.flowlet_time_diff = standard_metadata.ingress_global_timestamp - meta.flowlet_last_stamp;
                if (meta.flowlet_time_diff > FLOWLET_TIMEOUT)
                {
                    update_flowlet_id();
                }
            }

            @atomic
            {
                probe_handle_data_packet();
            }

            if (meta.dst_tor == meta.self_id)
            {
                edge_forward.apply();
            }
            else
            {
                hula_set_nhop.apply();
            }
        }
    }
}
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/
control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata)
{
    apply
    {
    }
}
/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/
control MyComputeChecksum(inout headers hdr, inout metadata meta)
{
    apply
    {
        update_checksum(
            hdr.ipv4.isValid(),
            {hdr.ipv4.version,
             hdr.ipv4.ihl,
             hdr.ipv4.dscp,
             hdr.ipv4.ecn,
             hdr.ipv4.totalLen,
             hdr.ipv4.identification,
             hdr.ipv4.flags,
             hdr.ipv4.fragOffset,
             hdr.ipv4.ttl,
             hdr.ipv4.protocol,
             hdr.ipv4.srcAddr,
             hdr.ipv4.dstAddr},
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}
/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/
// switch architecture
V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()) main;
