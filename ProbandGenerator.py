import os, sys
import pprint
import numpy as np


class FormatPrinter(pprint.PrettyPrinter):

    def __init__(self, formats, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formats = formats

    # overrides the default format method to use the custom formats for E, otherwise falls back to default formatting
    def format(self, obj, ctx, maxlvl, lvl):
        if type(obj) in self.formats:
            return self.formats[type(obj)].format(obj), 1, 0
        return pprint.PrettyPrinter.format(self, obj, ctx, maxlvl, lvl)


printer = FormatPrinter(
    {float: "{:.4e}"}, sort_dicts=False
)  #'{:.4e}'.format(3.14159) = '3.1416e+00' - formats E
# printer = FormatPrinter({},sort_dicts=False)


def broadcast_stack(arr, num):  # stacks arrays (copying arrays per given shape)
    arr = np.asarray(arr)
    return np.broadcast_to(arr, (num,) + arr.shape)



# create 128-byte integer for seed, everytime creates different seed to ensure randomness
seed = int.from_bytes(os.urandom(128), sys.byteorder)
# create random number generator with seed - same random numbers for same seed
# different random numbers for different seeds to ensure randomness
rng = np.random.default_rng(seed)

########################################## Create Scenes ##########################################
num_spots = 4
num_E_steps_per_decade = 6

E_decades_Evening = (-1, 0, 1, 2)  # 10^...
E_decades_Night = (-2, -1, 0, 1)  # 10^...


# horizontal stack of logarithmically spaced E values for evening [0.1lx ... 316lx], repeated for each decade,
E_steps_evening = np.hstack(
    [
        np.logspace(0, 1, num=num_E_steps_per_decade + 1)[:-1] * i
        for i in np.logspace(
            E_decades_Evening[0], E_decades_Evening[-1], len(E_decades_Evening)
        )
    ]
).tolist()[:-2]  # remove the last two values (464lx and 681lx)


num_E_steps_evening = len(E_steps_evening) #22
max_E_evening = E_steps_evening[-1]  # 316lx
E_steps_evening_repeated = np.tile(E_steps_evening, num_spots).tolist()  # repeat [0.1lx ... 316lx] for 4 spots then make list

# horizontal stack of logarithmically spaced E values for night [0.01lx ... 31.6lx], repeated for each decade,
E_steps_night = np.hstack(
    [
        np.logspace(0, 1, num=num_E_steps_per_decade + 1)[:-1] * i
        for i in np.logspace(
            E_decades_Night[0], E_decades_Night[-1], len(E_decades_Night)
        )
    ]
).tolist()[:-2]  # remove the last two values (46.4lx and 68.1lx)


num_E_steps_night = len(E_steps_night) #22
max_E_night = E_steps_night[-1]  # 31.6lx
E_steps_night_repeated = np.tile(E_steps_night, num_spots).tolist() #repeat [0.01lx ... 31.6lx] for 4 spots then make list

spots = np.arange(1, num_spots + 1)  # [1,2,3,4]
spooots_evening = np.repeat(spots, num_E_steps_evening).tolist() # ([1,2,3,4],22) = [1,1,1,...,2,2,2,...,3,3,3,...,4,4,4,...] 
spooots_night = np.repeat(spots, num_E_steps_night).tolist() # ([1,2,3,4],22) = [1,1,1,...,2,2,2,...,3,3,3,...,4,4,4,...] 


scenes_spots_evening = [
    {"ID": i + 1, "Zeit": "Abend", "Spot": s, "Farbe": "W1", "E": e} 
    for i, (s, e) in enumerate(zip(spooots_evening, E_steps_evening_repeated))
]

#{"ID": 1..22, "Zeit": "Abend", "Spot":1, "Farbe": "W1", "E": e}

print(scenes_spots_evening)

szenen_spots_nacht = [
    {"ID": i + 1 + scenes_spots_evening[-1]["ID"],"Zeit": "Nacht","Spot": s,"Farbe": "W1","E": e,}
    for i, (s, e) in enumerate(zip(spooots_night, E_steps_night_repeated))
]

szenen_diffus_abend = [
    {"ID": i + 1 + szenen_spots_nacht[-1]["ID"],"Zeit": "Abend","Spot": "diffus","Farbe": "W1","E": e,}
    for i, e in enumerate(E_steps_evening)
]
szenen_diffus_nacht = [
    {"ID": i + 1 + szenen_diffus_abend[-1]["ID"],"Zeit": "Nacht","Spot": "diffus","Farbe": "W1","E": e,}
    for i, e in enumerate(E_steps_night)
]

# need same IDs for szenen in both lists: generate fein first, grob is subset
grob_indizes_abend = np.arange(0, len(E_steps_evening), 3)
grob_indizes_abend_repeated = np.hstack(
    [grob_indizes_abend + i * (num_E_steps_evening) for i in range(num_spots)]
).tolist()
grob_indizes_nacht = np.arange(0, len(E_steps_night), 3)
grob_indizes_nacht_repeated = np.hstack(
    [grob_indizes_nacht + i * (num_E_steps_night) for i in range(num_spots)]
).tolist()

scenes_spots_evening_grob = [scenes_spots_evening[i] for i in grob_indizes_abend_repeated]
szenen_spots_nacht_grob = [szenen_spots_nacht[i] for i in grob_indizes_nacht_repeated]
szenen_diffus_abend_grob = [szenen_diffus_abend[i] for i in grob_indizes_abend]
szenen_diffus_nacht_grob = [szenen_diffus_nacht[i] for i in grob_indizes_nacht]

nr_wdh_grob = 1
nr_wdh_fein = 3
suchbereich_fein = 4  # in stufen +- um stoer E in feiner skala


E_vals_test = np.array([0.1, 3.1622777, 100]).tolist()
E_vals_test_repeated = np.tile(E_vals_test, num_spots).tolist()
spooots_test = np.repeat(spots, len(E_vals_test)).tolist()
szenen_test = [
    {"ID": -(i + 1), "Zeit": "Abend", "Spot": s, "Farbe": "W1", "E": e}
    for i, (s, e) in enumerate(zip(spooots_test, E_vals_test_repeated))
]


def get_E_idx(E_vals, Zeit):
    if Zeit == "Abend":
        E_idx = np.searchsorted(E_steps_evening, E_vals)
    elif Zeit == "Nacht":
        E_idx = np.searchsorted(E_steps_night, E_vals)
    else:
        raise ValueError("Invalid Zeit value. Must be 'Abend' or 'Nacht'.")
    return E_idx


def erzeuge_test_durchgang():
    durchgang = {"ID": -1, "Diffus": False, "Zeit": "Abend"}
    durchgang["Szenen"] = rng.permutation(szenen_test).tolist()
    with open("TestDurchgang.txt", "w") as file:
        file.write(printer.pformat(durchgang))


def erzeuge_lern_proband():
    proband = {"ID": -1, "Abstufung": "lernen"}
    durchgang = {"ID": -1, "Diffus": False, "Zeit": "Abend"}
    durchgang["Szenen"] = rng.permutation(szenen_test).tolist()
    proband["Durchgange"] = [durchgang]
    with open("ProbandLernen.txt", "w") as file:
        file.write(printer.pformat(proband))


def erzeuge_durchgange_diffus(proband_id, nr_wdh, szenen_abend, szenen_nacht):
    durchgange_diffus = []
    for zeit in ["Abend", "Nacht"] if proband_id & 1 else ["Nacht", "Abend"]:
        for w in range(1, nr_wdh + 1):
            duchgang_id = 1 + (zeit == "Nacht")  # 1,2
            durchgang = {
                "ID": duchgang_id,
                "Wiederholung": w,
                "Diffus": True,
                "Zeit": zeit,
            }
            durchgang["Szenen"] = rng.permutation(
                szenen_abend if zeit == "Abend" else szenen_nacht
            ).tolist()
            durchgange_diffus.append(durchgang)
    return durchgange_diffus


def erzeuge_durchgange_spots(proband_id, nr_wdh, szenen_abend, szenen_nacht):
    durchgange_spots = []
    for zeit in ["Abend", "Nacht"] if proband_id & 1 else ["Nacht", "Abend"]:
        for w in range(1, nr_wdh + 1):
            duchgang_id = 3 + (zeit == "Nacht")  # 3,4
            szenen = rng.permutation(
                szenen_abend if zeit == "Abend" else szenen_nacht
            ).tolist()
            # erste Hälfte der Szenen
            durchgang1 = {
                "ID": duchgang_id,
                "Wiederholung": w,
                "Diffus": False,
                "Zeit": zeit,
            }
            durchgang1["Szenen"] = szenen[: len(szenen) // 2]
            durchgange_spots.append(durchgang1)

            durchgang2 = {
                "ID": duchgang_id,
                "Wiederholung": w,
                "Diffus": False,
                "Zeit": zeit,
            }
            durchgang2["Szenen"] = szenen[len(szenen) // 2 :]
            durchgange_spots.append(durchgang2)
    return durchgange_spots


# grob enthält test-run mit
def erzeuge_probanden_grob(nr_probanden):
    for proband_id in range(1, nr_probanden + 1):
        proband = {"ID": proband_id, "Abstufung": "grob", "Lerndurchgang": False}
        durchgange_spots = erzeuge_durchgange_spots(
            proband_id, nr_wdh_grob, scenes_spots_evening_grob, szenen_spots_nacht_grob
        )
        durchgange_diffus = erzeuge_durchgange_diffus(
            proband_id, nr_wdh_grob, szenen_diffus_abend_grob, szenen_diffus_nacht_grob
        )
        if proband_id & 2:  # start with diffus
            proband["Durchgange"] = durchgange_spots + durchgange_diffus
        else:
            proband["Durchgange"] = durchgange_diffus + durchgange_spots
        with open("Proband{}_grob.txt".format(proband_id), "w") as file:
            file.write(printer.pformat(proband))


def sliding_window(min_idx, max_idx, middle_idx, window_half_size):
    num = max_idx - min_idx + 1
    window_size = 2 * window_half_size
    assert window_size <= num
    high_idx = np.minimum(middle_idx + window_half_size, max_idx + 1)
    low_idx = high_idx - window_size
    low_idx = np.maximum(low_idx, min_idx)
    high_idx = low_idx + window_size
    return low_idx, high_idx


def erzeuge_proband_fein(
    proband_id,
    stoer_E_spots_abend,
    stoer_E_spots_nacht,
    stoer_E_diffus_abend,
    stoer_E_diffus_nacht,
):  # stoer_E_grob ist die erste Beleuchtungsstärke die störend war
    proband = {"ID": proband_id, "Abstufung": "fein"}
    print(stoer_E_spots_abend)
    print(stoer_E_spots_nacht)
    print(stoer_E_diffus_abend)
    print(stoer_E_diffus_nacht)
    # sanetize input: arrays for stoer_E spots and stoer E diffus inputs can be None. Take max E if None
    stoer_E_spots_abend = (
        [max_E_evening] * 4
        if stoer_E_spots_abend is None
        else [max_E_evening if e is None else e for e in stoer_E_spots_abend]
    )
    stoer_E_spots_nacht = (
        [max_E_night] * 4
        if stoer_E_spots_nacht is None
        else [max_E_night if e is None else e for e in stoer_E_spots_nacht]
    )
    stoer_E_diffus_abend = (
        max_E_evening if stoer_E_diffus_abend is None else stoer_E_diffus_abend
    )
    stoer_E_diffus_nacht = (
        max_E_night if stoer_E_diffus_nacht is None else stoer_E_diffus_nacht
    )

    # Create Spot Durchgange
    scenes_spots_evening_custom = []
    szenen_spots_nacht_custom = []
    for i in range(num_spots):
        stoer_szene_spots_abend_idx = np.searchsorted(
            E_steps_evening, stoer_E_spots_abend[i]
        )
        stoer_szene_spots_nacht_idx = np.searchsorted(
            E_steps_night, stoer_E_spots_nacht[i]
        )
        spot_offset_abend = i * num_E_steps_evening
        spot_offset_nacht = i * num_E_steps_night
        spot_abend_low_idx, spot_abend_high_idx = sliding_window(
            0, num_E_steps_evening - 1, stoer_szene_spots_abend_idx, suchbereich_fein
        )
        scenes_spots_evening_custom.extend(
            scenes_spots_evening[
                spot_abend_low_idx
                + spot_offset_abend : spot_abend_high_idx
                + spot_offset_abend
            ]
        )
        spot_nacht_low_idx, spot_nacht_high_idx = sliding_window(
            0, num_E_steps_night - 1, stoer_szene_spots_nacht_idx, suchbereich_fein
        )
        szenen_spots_nacht_custom.extend(
            szenen_spots_nacht[
                spot_nacht_low_idx
                + spot_offset_nacht : spot_nacht_high_idx
                + spot_offset_nacht
            ]
        )

    durchgange_spots = erzeuge_durchgange_spots(
        proband_id, nr_wdh_fein, scenes_spots_evening_custom, szenen_spots_nacht_custom
    )

    # Create Diffus Durchgange
    stoer_szene_diffus_abend_idx = np.searchsorted(
        E_steps_evening, stoer_E_diffus_abend
    )
    stoer_szene_diffus_nacht_idx = np.searchsorted(E_steps_night, stoer_E_diffus_nacht)
    diffus_abend_low_idx, diffus_abend_high_idx = sliding_window(
        0, num_E_steps_evening - 1, stoer_szene_diffus_abend_idx, suchbereich_fein
    )
    szenen_diffus_abend_custom = szenen_diffus_abend[
        diffus_abend_low_idx:diffus_abend_high_idx
    ]
    diffus_nacht_low_idx, diffus_nacht_high_idx = sliding_window(
        0, num_E_steps_night - 1, stoer_szene_diffus_nacht_idx, suchbereich_fein
    )
    szenen_diffus_nacht_custom = szenen_diffus_nacht[
        diffus_nacht_low_idx:diffus_nacht_high_idx
    ]

    durchgange_diffus = erzeuge_durchgange_diffus(
        proband_id, nr_wdh_fein, szenen_diffus_abend_custom, szenen_diffus_nacht_custom
    )

    if proband_id & 2:  # start with diffus
        proband["Durchgange"] = durchgange_spots + durchgange_diffus
    else:
        proband["Durchgange"] = durchgange_diffus + durchgange_spots

    fname = "Proband{}_fein.txt".format(proband_id)
    if os.path.exists(fname):
        print(f"File {fname} already exists. Skipping.")
        return fname
    with open(fname, "w") as file:
        file.write(printer.pformat(proband))
    return fname


if __name__ == "__main__":
    erzeuge_probanden_grob(nr_probanden=5)
    erzeuge_lern_proband()
