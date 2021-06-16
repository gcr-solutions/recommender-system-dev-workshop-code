# Gen action.csv

import random
import time

with open('user.csv', 'r') as input_user:
    user_lines = input_user.readlines()

with open('item.csv', 'r') as input_item:
    item_lines = input_item.readlines()

user_id_list = []
item_id_list = []

for line in user_lines:
    user_id = line.split("_!_")[0]
    user_id_list.append(user_id)

for line in item_lines:
    item_id = line.split("_!_")[0]
    item_id_list.append(item_id)

print("len of user_id_list", len(user_id_list))
print("len of item_id_list", len(item_id_list))

action_list = []

for user_id in user_id_list:
    k = random.randint(1, 25)
    watch_list = random.sample(item_id_list, k=k)
    for item_id in watch_list:
        action_type = random.choices([1, 2], weights=[4, 6], k=1)[0]
        action_value = random.choices([0, 1], weights=[8, 2], k=1)[0]
        timestamp = int(time.time()) - random.randint(3600, 3600 * 24 * 60)
        source_type = random.choices([0, 1, 2, 3, 4], weights=[8, 1, 1, 1, 1], k=1)[0]
        action_list.append(
            "_!_".join([str(user_id), str(item_id), str(action_type), str(action_value), str(timestamp), str(source_type)]) + "\n")

print("len of action_list", len(action_list))

with open("action.csv", 'w') as out_acton:
    out_acton.writelines(action_list)

print("Done")
