import os

### Test setup ###


def set_UDP_buffer():
    os.system("""
        sudo sysctl -w net.core.rmem_max=26214400
        sudo sysctl -w net.core.rmem_default=26214400
    """)


def clean(n_client):
    os.system("""
        sudo ip netns del ns_src
        sudo ip netns del ns_mid

        rm -rf tmp  
    """)

    for i in range(n_client):
        os.system("sudo ip netns del ns_dst" + str(i))


def create_structure(n_client, file_size):
    os.system("mkdir tmp")
    for i in range(n_client):
        os.system("mkdir tmp/cli" + str(i) + "_d")

    serv_file = open("tmp/file.txt", "wb")
    serv_file.write(os.urandom(file_size))
    serv_file.close()


def create_namespaces(n_client):
    os.system("""
        sudo ip netns add ns_src
        sudo ip netns add ns_mid

        sudo ip link add ns_veth_s type veth peer name ns_veth_mids
    """)

    for i in range(n_client):
        os.system("sudo ip netns add ns_dst" + str(i))
        os.system(
            "sudo ip link add ns_veth_d"
            + str(i)
            + " type veth peer name ns_veth_midd"
            + str(i)
        )

    os.system("sleep 0.1")

    os.system("""
        sudo ip link set ns_veth_s netns ns_src
        sudo ip link set ns_veth_mids netns ns_mid

        sudo ip netns exec ns_src ip link set ns_veth_s up
        sudo ip netns exec ns_mid ip link set ns_veth_mids up
    """)

    for i in range(n_client):
        os.system("sudo ip link set ns_veth_midd" + str(i) + " netns ns_mid")
        os.system("sudo ip link set ns_veth_d" + str(i) + " netns ns_dst" + str(i))
        os.system(
            "sudo ip netns exec ns_dst"
            + str(i)
            + " ip link set ns_veth_d"
            + str(i)
            + " up"
        )
        os.system("sudo ip netns exec ns_mid ip link set ns_veth_midd" + str(i) + " up")


def setup_routing(n_client):
    os.system("""
        sudo ip netns exec ns_src ip addr add 10.0.0.1/24 dev ns_veth_s
        sudo ip netns exec ns_mid ip addr add 10.0.0.2/24 dev ns_veth_mids

        sudo ip netns exec ns_mid sysctl net.ipv4.ip_forward=1

        sudo ip netns exec ns_src ip route add default nexthop via 10.0.0.2 dev ns_veth_s weight 1

        sudo ip netns exec ns_mid smcrouted -l debug -I smctable
    """)

    str_if = ""

    for i in range(n_client):
        os.system(
            "sudo ip netns exec ns_dst"
            + str(i)
            + " ip addr add 10.1."
            + str(i)
            + ".1/24 dev ns_veth_d"
            + str(i)
        )
        os.system(
            "sudo ip netns exec ns_mid ip addr add 10.1."
            + str(i)
            + ".2/24 dev ns_veth_midd"
            + str(i)
        )
        os.system(
            "sudo ip netns exec ns_dst"
            + str(i)
            + " ip route add default nexthop via 10.1."
            + str(i)
            + ".2 dev ns_veth_d"
            + str(i)
            + " weight 1"
        )
        str_if += " ns_veth_midd" + str(i)

    os.system(
        "sudo ip netns exec ns_mid smcroutectl -I smctable add ns_veth_mids 239.239.239.35"
        + str_if
    )


def set_delay(delay, n_client, mode=0):
    """mode:
    0 -> normal
    1 -> the higher the client number the more delayed
    2 -> the higher the client number the less delayed
    3 -> the first client is more delayed
    4 -> the first client is less delayed
    """
    if not delay:
        return

    os.system(
        "sudo ip netns exec ns_src tc qdisc add dev ns_veth_s root netem delay "
        + str(delay)
        + "ms"
    )

    for i in range(n_client):
        cmd = (
            "sudo ip netns exec ns_dst"
            + str(i)
            + " tc qdisc add dev ns_veth_d"
            + str(i)
            + " root netem delay "
        )
        match mode:
            case 0:
                cmd += str(delay)
            case 1:
                cmd += str(delay // (n_client - i))
            case 2:
                cmd += str(delay // (i + 1))
            case 3:
                cmd += str(delay // (2 - 1 * (i == 0)))
            case 4:
                cmd += str(delay // (2 - 1 * (i != 0)))
            case _:
                cmd += str(delay)

        os.system(cmd + "ms")


def final_clean(n_client):
    if input("Clean the room ? [y/N]") in ["Y", "y"]:
        clean(n_client)


### Analyse ###


def concatenate_events(file_size, li_events):
    li_conc = []
    for i, off, length in li_events:
        li_conc.append((i, off, off + length - 1))
    li_conc.sort(key=lambda x: (x[0] + 1) * file_size + off)
    for i in range(len(li_conc) - 1, 0, -1):
        if (
            li_conc[i][0] == li_conc[i - 1][0]
            and li_conc[i][1] == li_conc[i - 1][2] + 1
        ):
            li_conc[i - 1] = (li_conc[i][0], li_conc[i - 1][1], li_conc[i][2])
            li_conc.pop(i)
    return li_conc


def missing_pkt(li, file_size, avg_pkt_len):
    end, mid = avg_pkt_len, avg_pkt_len // 2
    pn = 2
    missing_pkt_li = []
    while end < file_size:
        end += avg_pkt_len
        b = 0
        for i, d, f in li:
            b = b or (d < mid and mid < f)
        if not b:
            missing_pkt_li.append(pn)
        pn += 1
        mid += avg_pkt_len
    return missing_pkt_li
