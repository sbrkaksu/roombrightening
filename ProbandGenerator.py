import os,sys
import pprint
import numpy as np

class FormatPrinter(pprint.PrettyPrinter):

    def __init__(self, formats, *args, **kwargs):
        super(FormatPrinter, self).__init__(*args, **kwargs)
        self.formats = formats

    def format(self, obj, ctx, maxlvl, lvl):
        if type(obj) in self.formats:
            return self.formats[type(obj)].format(obj), 1, 0
        return pprint.PrettyPrinter.format(self, obj, ctx, maxlvl, lvl)

printer = FormatPrinter({float: "{:.4e}"},sort_dicts=False)
printer = FormatPrinter({},sort_dicts=False)
def broadcast_stack(arr,num): # stacks arrays
    return np.broadcast_to(arr,(num,)+arr.shape)

seed = int.from_bytes(os.urandom(128),sys.byteorder)
rng = np.random.default_rng(seed)

num_spots = 4
num_E_dekaden = 4
num_E_stufen_fein = 6
num_E_fein = num_E_stufen_fein * num_E_dekaden
suchbereich_fein = 3 # in stufen +- um stoer E in feiner skala

spots = np.arange(1,num_spots+1)
spooots = np.repeat(spots,num_E_fein).tolist()

E_vals_fein = np.hstack([np.logspace(0,1,num=num_E_stufen_fein+1)[:-1] * i for i in np.logspace(-2,1,num=num_E_dekaden)]).tolist()
E_vals_fein_repeated = np.tile(E_vals_fein,num_spots).tolist()
szenen_spots_fein = [{"ID":i+1, "Spot":s, "Farbe":"W1", "E":e} for i,(s,e) in enumerate(zip(spooots,E_vals_fein_repeated))]

szenen_diffus_fein = [{"ID":i+1+len(szenen_spots_fein), "Spot":"diffus", "Farbe":"W1", "E":e} for i,e in enumerate(E_vals_fein)]

# need same IDs for szenen in both lists: generate fein first, grob is subset
szenen_spots_grob = szenen_spots_fein[::3]
szenen_diffus_grob = szenen_diffus_fein[::3]

nr_wdh_grob = 1
nr_wdh_fein = 3

E_vals_test = np.array([ 0.031622777, 0.31622777, 10.]).tolist()
E_vals_test_repeated = np.tile(E_vals_test,num_spots).tolist()
spooots_test = np.repeat(spots,len(E_vals_test)).tolist()
szenen_spots_test = [{"ID":-(i+1), "Spot":s, "Farbe":"W1", "E":e} for i,(s,e) in enumerate(zip(spooots_test,E_vals_test_repeated))]

def erzeuge_test_durchgang():
    durchgang = {"ID":-1 , "Typ":"Test", "Diffus": False, "Position": "Sitzen"}
    durchgang["Szenen"] = rng.permutation(szenen_spots_test).tolist()
    return durchgang

def erzeuge_durchgange(proband_id, nr_wdh, szenen_diffus, szenen_spots, typ):
    durchgange = []
    # Reihenfolge von Diffus und Position ist deterministisch, 4 Varianten gleich häufig
    for diffus in[False, True] if proband_id & 2 else [True, False]:
        for position in ["Sitzen", "Liegen"] if proband_id & 1 else ["Liegen", "Sitzen"]:
            for w in range(1, nr_wdh+1):
                duchgang_id = 1 + (position == "Sitzen") + diffus * 2 # 1,2,3,4
                durchgang = {"ID":duchgang_id , "Typ":typ, "Diffus": diffus, "Position": position}
                durchgang["Szenen"] = rng.permutation(szenen_diffus if diffus == True else szenen_spots).tolist()
                durchgange.append(durchgang)
    return durchgange

# grob enthält test-run mit 
def erzeuge_probanden_grob(nr_probanden):
    for i in range(1, nr_probanden+1): 
        proband = {"ID": i, "Abstufung":'grob', "Durchgange": []}
        proband["Durchgange"].append(erzeuge_test_durchgang())
        proband["Durchgange"].extend(erzeuge_durchgange(i,nr_wdh_grob, szenen_diffus_grob, szenen_spots_grob,"Grob"))
        with open("Proband{}_grob.txt".format(i),"w") as file:
            file.write(printer.pformat(proband))
            #pprint.pp(proband, file)

def erzeuge_proband_fein(proband_id, stoer_E_spots, stoer_E_diffus): # stoer_E_grob ist die erste Beleuchtungsstärke die störend war
    proband = {"ID": proband_id, "Abstufung":'fein', "Durchgange": []}
    stoer_E_spots_idxes = np.searchsorted(E_vals_fein, stoer_E_spots)
    E_range_spots_high_idx = np.minimum(stoer_E_spots_idxes + suchbereich_fein + 1, len(E_vals_fein) - 1) # +1 wegen list slicing
    E_range_spots_low_idx = np.maximum(stoer_E_spots_idxes - suchbereich_fein - 2 , 0) # -2, ist nicht störende E in grober skala
    szenen_spot_custom_slices = [slice(E_range_spots_low_idx[i] + i * num_E_fein,E_range_spots_high_idx[i]+ i * num_E_fein) for i in range(num_spots)]
    szenen_spots_custom = []
    for i in range(num_spots):
        szenen_spots_custom.extend(szenen_spots_fein[szenen_spot_custom_slices[i]]) 
    
    stoer_E_diffus_idx = np.searchsorted(E_vals_fein, stoer_E_diffus)
    E_range_diffus_high_idx = np.minimum(stoer_E_diffus_idx + suchbereich_fein + 1, len(E_vals_fein) - 1) # +1 wegen list slicing
    E_range_diffus_low_idx = np.maximum(stoer_E_diffus_idx - suchbereich_fein - 2 , 0) # -2, ist nicht störende E in grober skala
    szenen_diffus_custom = szenen_diffus_fein[E_range_diffus_low_idx:E_range_diffus_high_idx]
    
    proband["Durchgange"] = erzeuge_durchgange(proband_id,nr_wdh_fein, szenen_diffus_custom, szenen_spots_custom,"Fein")
    with open("Proband{}_fein.txt".format(proband_id),"w") as file:
        file.write(printer.pformat(proband))
        #pprint.pp(proband, file)

erzeuge_probanden_grob(nr_probanden = 50)

E_vals_grob = E_vals_fein[::3]
stoer_E_spots = E_vals_grob[2:6] # for testing the fine generator
stoer_E_spots = [E_vals_grob[3],E_vals_grob[4],E_vals_grob[3],E_vals_grob[3]]
erzeuge_proband_fein(1,stoer_E_spots,1)

proband = {
            "ID": 1,
            "Durchgange":[
                {
                    "ID" : 1,
                    "Matt": False,
                    "Szenen" : [
                        {"ID": 1, "Spot" : 1, "Farbe":"W1", "E" : 30},
                        {"ID": 2, "Spot" : 2, "Farbe":"W1", "E" : 1},
                        {"ID": 3, "Spot" : 1, "Farbe":"W1", "E" : 6},
                        {"ID": 4, "Spot" : 2, "Farbe":"W1", "E" : 0.1},
                        {"ID": 5, "Spot" : 4, "Farbe":"W1", "E" : 30},
                        {"ID": 6, "Spot" : 4, "Farbe":"W1", "E" : 100}
                        ]
                },
                {
                    "ID" : 2,
                    "Matt": False,
                    "Szenen" : [
                        {"ID": 1, "Spot" : 1, "E" : 30},
                        {"ID": 2, "Spot" : 3, "E" : 1},
                        {"ID": 3, "Spot" : 4, "E" : 6},
                        {"ID": 4, "Spot" : 2, "E" : 0.3},
                        {"ID": 5, "Spot" : 4, "E" : 10},
                        {"ID": 6, "Spot" : 3, "E" : 60}
                        ]
                },
                {
                    "ID" : 3,
                    "Matt": True,
                    "Szenen" : [
                        {"ID": 1, "Spot" : 4, "E" : 30},
                        {"ID": 2, "Spot" : 2, "E" : 1},
                        {"ID": 3, "Spot" : 4, "E" : 6},
                        {"ID": 4, "Spot" : 2, "E" : 0.1},
                        {"ID": 5, "Spot" : 4, "E" : 30},
                        {"ID": 6, "Spot" : 1, "E" : 100}
                        ]
                }
            ]
        }