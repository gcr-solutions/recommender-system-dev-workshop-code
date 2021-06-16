import random
import time
from time import gmtime, strftime
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
        item_id = item_line.split("_!_")[0]
        items_ids.append(item_id)

print("user_ids:", len(user_ids))
print("items_ids:", len(items_ids))

clink_lines = []
for user_id in user_ids:
    clicked_items_ids = random.choices(items_ids, k=random.randint(1, 3))
    n = 0
    for item_id in clicked_items_ids:
        n = n + 1
        clicked_time = int(time.time()) - random.randint(0, 3600 * 6) + n
        clicked = random.choices([0, 1], weights=[7, 3])[0]
        clink_line = "_!_".join([str(user_id), str(item_id), str(clicked_time), "1", str(clicked) ])
        clink_lines.append(clink_line)

timestamp = strftime('%Y-%m-%dT%H:%M:%S', gmtime())
with open(f"action_{timestamp}.csv", 'w') as out:
    for line in clink_lines:
        out.write(line + "\n")
