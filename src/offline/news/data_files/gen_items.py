import random
import re
from time import strftime, gmtime

regexp = re.compile(r'[&`><=@ω\{\}^#$/\]\[*【】Ⅴ；%+——「」｜…….:。\s？.：·、！《》!,，_~)）（(?“”"\\-]')

item_raw_arr = []

with open("item.csv", 'w') as item_out:
    with open("news_raw.csv") as item_in:
        while True:
            item_line = item_in.readline().strip()
            if item_line == "":
                break
            item_arr = item_line.split("_!_")
            title = item_arr[3]
            title_clean = regexp.sub("",  title)
            item_arr[3] = title_clean
            item_arr.append(str(random.randint(0, 10)))
            item_arr.append(str(random.choices([1, 0], weights=[2, 8])[0]))

            item_out.write("_!_".join(item_arr) + "\n")
            item_raw = item_arr.copy()
            item_raw[3] = title
            item_raw_arr.append("_!_".join(item_raw))

timestamp = strftime('%Y-%m-%dT%H:%M:%S', gmtime())
with open(f"item_{timestamp}.csv", 'w') as out:
    for line in item_raw_arr:
        out.write(line + "\n")
