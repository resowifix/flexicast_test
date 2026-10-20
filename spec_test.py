import os
import subprocess
import time
import lib as l

n_client = 2
packet_lost = [
    "",
    "2,",
    "10,12,17,",
    "6,7,12,13,14,",
    "7,14,",
    "4,5,9,",
    "7,11,12,16,",
    "8,11,15,",
    "3,5,10,11,13,",
    "3,10,17,",
    "3,6,",
    "2,10,12,",
    "6,",
    "9,12,13,16,",
    "4,6,8,9,12,",
    "10,",
    "6,12,",
] + 25 * [""]
file_size = 20000
delay = 0
wireshark = 1
auto = True

wireshark_path = "/home/broisou/build/wireshark/build/run/wireshark"
quiche_path = "../multicast-quic/"
picoquic_path = "./"
keylog_file = "/home/broisou/sslkeylogfile.log"

l.set_UDP_buffer()

l.clean(n_client)

time.sleep(0.1)

l.create_structure(n_client, file_size)

time.sleep(0.1)

# Create namespace


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
    # Give the time to open the right interface
    time.sleep(10)

log_file = open("tmp/log_" + str(n_client) + "_0", "w")

os.system(
    "echo '"
    + 'QLOGDIR="./tmp" RUST_LOG=trace '
    + quiche_path
    + "target/debug/fc-flow-file-transfer "
    + "--src 10.0.0.1:4678 --fc-timer adaptive "
    + "--cert-path "
    + quiche_path
    + "apps/src/bin/ --mc-addr 239.239.239.35:4444 "
    + "--ctl-ack-delay 0 --fc-cwnd cubic --transfer-kind file,file,tmp/file.txt "
    + "--unicast --flexicast --initial-fc-flow 10000000000 --wait "
    + str(n_client)
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

print("\nGo !\n")

cli_process = []
log_cli = []
for i in range(n_client):
    log_cli.append(open("./tmp/cli" + str(i) + "_d/log", "w"))
    os.system(
        "echo 'export SSLKEYLOGFILE="
        + keylog_file
        + "\n"
        + picoquic_path
        + "picoquic_fc 10.0.0.1 4678 tmp/cli"
        + str(i)
        + "_d/ 1 "
        + packet_lost[i]
        + "' > tmp/cli"
        + str(i)
        + "_d/client_lch.sh"
    )
    os.system("chmod +x tmp/cli" + str(i) + "_d/client_lch.sh")
    cli_process.append(
        subprocess.Popen(
            [
                "sudo",
                "ip",
                "netns",
                "exec",
                "ns_dst" + str(i),
                "./tmp/cli" + str(i) + "_d/client_lch.sh",
            ],
            stdout=log_cli[i],
            stderr=log_cli[i],
        )
    )

# Continue when all client are done
while sum([c.poll() is None for c in cli_process]) != 0:
    None

time.sleep(0.1)

for f in log_cli:
    f.close()

serv.kill()
log_file.close()

ret = []
for i in range(n_client):
    r = not (not (os.system("diff tmp/file.txt tmp/cli" + str(i) + "_d/file0")))
    ret.append(r)
    if r:
        os.system("echo -e '\nNN' >> tmp/cli" + str(i) + "_d/log")
    else:
        os.system("echo -e '\nGG' >> tmp/cli" + str(i) + "_d/log")
    os.system("sudo rm tmp/cli" + str(i) + "_d/file0")

os.system("sudo ./rm_all 1> /dev/null 2>&1")

print("Fin", ret, sum(ret))

# Wait for wireshark to be closed
while wireshark and w.poll() is None:
    None

dev_null.close()

if not auto:
    l.final_clean(n_client)

exit(sum(ret) != 0)
