import glob
import os
import random
import shutil
user_ids = []
items_ids = []

with open("user.csv") as user_in:
    while True:
        user_line = user_in.readline().strip()
        if not user_line:
            break
        user_id = user_line.split("_!_")[0]
        user_ids.append(user_id)

with open("item.csv") as user_in:
    while True:
        item_line = user_in.readline().strip()
        if not item_line:
            break
        item_id, item_type_code = item_line.split("_!_")[0:2]
        items_ids.append([item_id, item_type_code])

print("user_ids:", len(user_ids))
print("items_ids:", len(items_ids))


def find_item_type_code(item_id):
    code = None
    for it_id, it_type_code in items_ids:
        if str(it_id) == str(item_id):
            code = it_type_code
            break
    if code:
        return code
    else:
        raise Exception()

action_file_final = "action_ingest.csv"
if os.path.exists(action_file_final):
    os.remove(action_file_final)

clicked_action = []
for action_file in glob.glob("action*.csv"):
    print("process {}".format(action_file))
    with open(action_file, "r") as input:
        while True:
            line = input.readline().strip()
            if not line:
                break
            item_id = line.split("_!_")[1]
            item_type_code = find_item_type_code(item_id)
            if random.randint(0,10) > 5:
                item_type_code = 1
            clicked_action.append(f"{line}_!_{item_type_code}\n")


with open(action_file_final, "w") as out:
    out.writelines(clicked_action)
