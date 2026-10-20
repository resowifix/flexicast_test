import os

r = 0

for i in range(100):
    r += not(not(os.system("python spec_test.py")))
    print("RES_PART", i, ":", r)

print("END:", r)