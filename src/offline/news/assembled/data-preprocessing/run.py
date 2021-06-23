import argparse
import subprocess


def run_script(cmds_arr):
    print("run_script: '{}'".format(" ".join(cmds_arr)))
    re_code, out_msg = subprocess.getstatusoutput(cmds_arr)
    print("run_script re_code:", re_code)
    for line in out_msg.split("\n"):
        print(line)
    if re_code != 0:
        raise Exception(out_msg)


parser = argparse.ArgumentParser(description="app inputs and outputs")
parser.add_argument("--bucket", type=str, help="s3 bucket")
parser.add_argument("--prefix", type=str,
                    help="s3 input key prefix")

args = parser.parse_args()

print("args:", args)
bucket = args.bucket
prefix = args.prefix
if prefix.endswith("/"):
    prefix = prefix[:-1]

print(f"bucket:{bucket}, prefix:{prefix}")
run_script([f"./run.sh {bucket} {prefix}"])
