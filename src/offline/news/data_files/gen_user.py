import random
import time
import uuid
import random_username
from random_username.generate import generate_username

N = 0
# with open('user.csv', "w") as out:
#     while N < 1000:
#         N = N + 1
#         user_id = str(uuid.uuid1())
#         sex = random.choices(["M", "F"], weights=[4, 6])[0]
#         age = random.choices([12, 18, 25, 35, 48, 59, 65, 75],
#                              weights=[1, 3, 5, 5, 4, 4, 2, 1])[0] + random.randint(-3, 3)
#         register_time = int(time.time()) - random.randint(3600 * 24 * 10, 3600 * 24 * 30)
#         user_info = [user_id, str(sex), str(age), str(register_time)]
#         line = "_!_".join(user_info)
#         out.write(line + "\n")


users = []
with open('user.csv') as input:
    while True:
        line = input.readline()
        if not line:
            break
        user_items = line.strip().split("_!_")
        id = user_items[0]
        sex = user_items[1]
        age = user_items[2]
        time = user_items[3]
        name = generate_username()[0]
        new_user = "_!_".join([str(id), str(sex), str(age), str(time), str(name)])
        users.append(new_user)

with open('user_1.csv', 'w') as out:
    out.write("\n".join(users))


