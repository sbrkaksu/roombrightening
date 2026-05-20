import numpy as np

num_E_steps_per_decade = 6

E_decades_Evening = (-1, 0, 1, 2)  # 10^...
E_decades_Night = (-2, -1, 0, 1)  # 10^...


E_steps_evening = np.hstack(
    [
        np.logspace(0, 1, num=num_E_steps_per_decade + 1)[:-1] * i
        for i in np.logspace(
            E_decades_Evening[0], E_decades_Evening[-1], len(E_decades_Evening)
        )
    ]
).tolist()[:-2]

print(np.logspace(0, 1, 7)[:-1] * 10)
