import argparse
import subprocess
import os
import json


def run_script(cmds_arr):
    print("run_script: '{}'".format(" ".join(cmds_arr)))
    re_code, out_msg = subprocess.getstatusoutput(cmds_arr)
    print("run_script re_code:", re_code)
    for line in out_msg.split("\n"):
        print(line)
    if re_code != 0:
        raise Exception(out_msg)


param_path = os.path.join('/opt/ml/', 'input/config/hyperparameters.json')
parser = argparse.ArgumentParser()
if os.path.exists(param_path):
    print("load param from {}".format(param_path))
    with open(param_path) as f:
        hp = json.load(f)
        print("hyperparameters:", hp)
        bucket = hp['bucket']
        prefix = hp['prefix']
else:
    # running processing job
    parser.add_argument('--bucket', type=str)
    parser.add_argument('--prefix', type=str)
    args, _ = parser.parse_known_args()
    bucket = args.bucket
    prefix = args.prefix

if prefix.endswith("/"):
    prefix = prefix[:-1]

print(f"bucket:{bucket}, prefix:{prefix}")
run_script([f"./run.sh {bucket} {prefix}"])
