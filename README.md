# Picoquic flexicast testing material

## Manual testing

`setup_netns` set up a namespace environment to launch manually two clients, a server, and more if needed.

```text
                            +-------------+
                            |   ns_src    |
                            |             |
                            |  10.0.0.1   |---+
                            | 2001:db0::1 |   | 239.239.239.35
                            +-------------+   |
                                   ^          |
                                   |          |
                                   v          |
                    +-------------------------|-----+
                    |          10.0.0.2       |     |
                    |         2001:db0::2     |     |
                    |                         |     |
                    |            ns_mid       |     |
                    |               +---------+     |
                    |  10.0.2.2     |    10.0.3.2   |
                    | 2001:db2::2 <-+-> 2001:db3::2 |
                    +-------------------------------+
                           ^                 ^
                           |                 |
                           v                 v
                    +------+------+   +------+------+
                    |  10.0.2.1   |   |  10.0.3.1   |
                    | 2001:db2::1 |   | 2001:db3::1 |
                    |             |   |             |
                    |   ns_dst0   |   |   ns_dst1   |
                    +-------------+   +-------------+
```

To access to a node use `$ _ ip netns exec <node ex: ns_src> bash`.

## Large testing

`megatest_fuzz.py` make several tests with some randomness in order to make errors appear.

Some parameters must be set before use:

- `n_client`, the maximum number of client that will be involved in a test,
- `n_test`, the number of run,
- `lost_proba`, the probability for a packet to be lost,
- `file_size`, the size of the file to be sent during tests (max 20000),
- `delay`
- `wireshark`, launch wireshark on `ns_mid` if set to `True`,
- `wireshark_path`, path to wireshark binary,
- `quiche_path`, the multicast-quic quiche folder path,
- `picoquic_path`, the folder path where `picoquic_fc` executable is (usually picoquic folder path),
- `keylog_file`, the path of the file where secrets enabling decryption will be stored.

All results are stored in `./tmp` folder.

`analyse_fuzz.py` can be used to summerize the result of `megatest_fuzz.py`. Some parameters must also be set according to the settings of `megatest_fuzz.py`.

## Specific testing

`spec_test.py` make only one run of `megatest_fuzz.py`, with all parameters set. `rep_test.py` repeat several time `spec_test.py` to analyse repetability.
