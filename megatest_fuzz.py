import os
import subprocess
import random
import time
import lib as l

n_client = 25
n_test = 10
lost_proba = 0.2
file_size = 20000
delay = 0
wireshark = 0
avg_pkt_len = 1310

wireshark_path = "/home/broisou/Documents/stage/wireshark/build/run/wireshark"
quiche_path = "../multicast-quic/"
picoquic_path = "./"
keylog_file = "/home/broisou/sslkeylogfile.log"

l.set_UDP_buffer()

l.clean(n_client)

time.sleep(0.1)

l.create_structure(n_client, file_size)

time.sleep(0.1)

l.create_namespaces(n_client)

time.sleep(0.1)

l.setup_routing(n_client)

l.set_delay(delay, n_client)

dev_null = open("/dev/null")

if wireshark:
    w = subprocess.Popen(
        ["sudo", "ip", "netns", "exec", "ns_mid", wireshark_path],
        stdout=dev_null,
        stderr=dev_null,
    )
    time.sleep(6)

for i in range(n_test):
    nc_up = random.randrange(2, n_client + 1)

    os.system("mkdir tmp/serv_" + str(i))
    log_file = open("tmp/serv_" + str(i) + "/log", "w")

    os.system(
        "echo '"
        + 'QLOGDIR="./tmp/serv_'
        + str(i)
        + '" RUST_LOG=trace '
        + quiche_path
        + "/target/debug/fc-flow-file-transfer "
        + "--src 10.0.0.1:4678 --fc-timer adaptive "
        + "--cert-path "
        + quiche_path
        + "/apps/src/bin/ --mc-addr 239.239.239.35:4444 "
        + "--ctl-ack-delay 0 --fc-cwnd cubic --transfer-kind file,file,tmp/file.txt "
        + "--unicast --flexicast --initial-fc-flow 10000000000 --wait "
        + str(nc_up)
        + " --mc-src-addr 10.0.0.1:4443 "
        + "--fall-back-delay 2000' > ./tmp/quiche_lch.sh"
    )
    os.system("chmod +x ./tmp/quiche_lch.sh")

    time.sleep(0.1)

    serv = subprocess.Popen(
        ["sudo", "ip", "netns", "exec", "ns_src", "./tmp/quiche_lch.sh"],
        stdout=log_file,
        stderr=log_file,
    )

    time.sleep(0.5)

    os.system("reset -w")

    print("Go", i, ", nc_up:", nc_up)

    cli_process = []
    log_cli = []
    for c in range(nc_up):
        log_cli.append(open("tmp/cli" + str(c) + "_d/log_" + str(i), "w"))
        cmd = (
            "echo 'SSLKEYLOGFILE="
            + keylog_file
            + "\n"
            + picoquic_path
            + "picoquic_fc 10.0.0.1 4678 tmp/cli"
            + str(c)
            + "_d/ 1 "
        )
        if c != 0:
            lost_pkt = ""
            for j in range(3, 2 + file_size // avg_pkt_len + 1):
                if random.random() < lost_proba:
                    lost_pkt += str(j)
                    lost_pkt += ","

            print(lost_pkt, end='", "')

            os.system(cmd + lost_pkt + "' > tmp/cli" + str(c) + "_d/client_lch.sh")
        else:
            os.system(cmd + "' > tmp/cli" + str(c) + "_d/client_lch.sh")

        os.system("chmod +x tmp/cli" + str(c) + "_d/client_lch.sh")
        cli_process.append(
            subprocess.Popen(
                [
                    "sudo",
                    "ip",
                    "netns",
                    "exec",
                    "ns_dst" + str(c),
                    "./tmp/cli" + str(c) + "_d/client_lch.sh",
                ],
                stdout=log_cli[c],
                stderr=log_cli[c],
            )
        )

    os.system("reset -w")
    print()

    while sum([c.poll() is None for c in cli_process]) != 0:
        None

    time.sleep(0.1)

    for f in log_cli:
        f.close()

    serv.kill()
    log_file.close()

    for c in range(nc_up):
        if os.system("diff tmp/file.txt tmp/cli" + str(c) + "_d/file0"):
            os.system("echo -e '\nNN' >> tmp/cli" + str(c) + "_d/log_" + str(i))
        else:
            os.system("echo -e '\nGG' >> tmp/cli" + str(c) + "_d/log_" + str(i))
        os.system("sudo rm tmp/cli" + str(c) + "_d/file0")

    os.system("sudo ./rm_all 1> /dev/null 2>&1")

    print("Fin")


while wireshark and w.poll() is None:
    None

dev_null.close()

time.sleep(0.1)

l.final_clean(n_client)
