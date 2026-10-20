import os
import lib as l

n_clients = 25
n_tests = 100
file_size = 20000
dir = "tmp"
avg_pkt_len = 1310

n_packets = file_size // 1310 + 1

res = [[-1] * n_clients for i in range(n_tests)]


for c in range(n_clients):
    for t in range(n_tests):
        if os.path.isfile(dir + "/cli" + str(c) + "_d/log_" + str(t)):
            f = open(dir + "/cli" + str(c) + "_d/log_" + str(t), "r")
            li_events = []
            for li in f:
                if "fault" in li or "Fault" in li:
                    res[t][c] = [(3, 0, 0)]
                    break
                if "bzz" in li:
                    li_events.append([int(i) for i in li.split()[1:]])
                if "GG" in li:
                    res[t][c] = [(3, 0, file_size)]
                    break
                if "NN" in li:
                    res[t][c] = l.concatenate_events(file_size, li_events)
                    break
            f.close()
        elif c == 0:
            n_tests = t
            print("n_tests set to", t)
            res = res[:n_tests]
            break

fr = []


for t in range(len(res)):
    print("test", t, end=", client with problems: {")
    for c in range(len(res[t])):
        rp = res[t][c]
        if rp == -1:
            print("}, nb_client:", c, end="")
            break
        if rp != -1 and (len(rp) != 1 or rp[0][1] != 0 or rp[0][2] != file_size):
            if len(rp) > 0 and rp[0][1] == 0 and rp[0][2] == 0:
                print("seg", end="")
            fr.append((t, c, l.missing_pkt(rp, file_size, avg_pkt_len)))
            print(c, end=", ")
    print()

print("run, client, ids_packet_lost")
print(fr)
