with open('action.csv', 'r') as input_item:
    lines = input_item.readlines()

new_lines = []
for line in lines:
    items = line.split("_!_")  # 22780_!_611_!_2_!_0_!_1617488831_!_1
    # 250def1d50bf_!_1690341_!_1621319827_!_1_!_0_!_1
    new_line = [items[0], items[1], items[4], items[2], items[3], items[5]]
    new_lines.append("_!_".join(new_line))

with open('action_2.csv', 'w') as out:
    out.writelines(new_lines)
