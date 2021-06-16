import json
from collections import Counter

with open('item.csv', 'r') as input_item:
    item_lines = input_item.readlines()

n = 0
type_list = []
for line in item_lines:
    movie_type = line.split("_!_")[6]
    movie_types = movie_type.split("|")
    type_list.extend(movie_types)

c = Counter(type_list)
print(json.dumps(c, indent=2))
print(c.most_common(10))

cat = [x for x, _ in c.most_common(10)]

save_lines = []
for line in item_lines:
    item_line = line.split("_!_")
    movie_type_col = item_line[6]
    movie_types = movie_type_col.split("|")
    save_types = []
    for c in movie_types:
        if c in cat:
            save_types.append(c)
    if len(save_types) == 0:
        save_types = ['drama']

    item_line[6] = "|".join(save_types)
    save_lines.append("_!_".join(item_line))


with open('item_cat.csv', 'w') as out:
    out.writelines(save_lines)