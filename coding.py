import os
import sys
import numpy as np

scenes = np.array(np.concatenate(([0] * 30, [1] * 30)))

seed = int.from_bytes(os.urandom(128), sys.byteorder)
rng = np.random.default_rng(seed)

combined_scenes = rng.permutation(scenes).tolist()


for i in range(len(combined_scenes)): 
    #print(combined_scenes[i])
    pass

print(combined_scenes)
print("\n")

print(len(combined_scenes))
