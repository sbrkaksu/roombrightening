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
#printer = FormatPrinter({},sort_dicts=False)

def broadcast_stack(arr,num): # stacks arrays
    return np.broadcast_to(arr,(num,)+arr.shape)

seed = int.from_bytes(os.urandom(128),sys.byteorder)
rng = np.random.default_rng(seed)

########################################## Szenen erzeugen ##########################################
num_spots = 4
E_dekaden_abend = (-1,0,1) # 10^...
E_dekaden_nacht = (-2,-1,0,1) # 10^...
num_E_stufen_pro_dekade = 6
E_stufen_abend = np.hstack([np.logspace(0,1,num=num_E_stufen_pro_dekade+1)[:-1] * i for i in np.logspace(E_dekaden_abend[0],E_dekaden_abend[-1],len(E_dekaden_abend))]).tolist()[:-2]
num_E_stufen_abend = len(E_stufen_abend)
E_stufen_abend_repeated = np.tile(E_stufen_abend,num_spots).tolist()

E_stufen_nacht = np.hstack([np.logspace(0,1,num=num_E_stufen_pro_dekade+1)[:-1] * i for i in np.logspace(E_dekaden_nacht[0],E_dekaden_nacht[-1],len(E_dekaden_nacht))]).tolist()[:-2]
num_E_stufen_nacht = len(E_stufen_nacht)
E_stufen_nacht_repeated = np.tile(E_stufen_nacht,num_spots).tolist()

spots = np.arange(1,num_spots+1)
spooots_abend = np.repeat(spots,num_E_stufen_abend).tolist()
spooots_nacht = np.repeat(spots,num_E_stufen_nacht).tolist()

szenen_spots_abend = [{"ID":i+1, "Zeit":"Abend", "Spot":s, "Farbe":"W1", "E":e} for i,(s,e) in enumerate(zip(spooots_abend,E_stufen_abend_repeated))]
szenen_spots_nacht = [{"ID":i+1+szenen_spots_abend[-1]['ID'], "Zeit":"Nacht", "Spot":s, "Farbe":"W1", "E":e} for i,(s,e) in enumerate(zip(spooots_nacht,E_stufen_nacht_repeated))]

szenen_diffus_abend = [{"ID":i+1+szenen_spots_nacht[-1]['ID'], "Zeit":"Abend", "Spot":"diffus", "Farbe":"W1", "E":e} for i,e in enumerate(E_stufen_abend)]
szenen_diffus_nacht = [{"ID":i+1+szenen_diffus_abend[-1]['ID'], "Zeit":"Nacht", "Spot":"diffus", "Farbe":"W1", "E":e} for i,e in enumerate(E_stufen_nacht)]
# need same IDs for szenen in both lists: generate fein first, grob is subset
szenen_spots_abend_grob = szenen_spots_abend[::3]
szenen_spots_nacht_grob = szenen_spots_nacht[::3]
szenen_diffus_abend_grob = szenen_diffus_abend[::3]
szenen_diffus_nacht_grob = szenen_diffus_nacht[::3]

nr_wdh_grob = 1
nr_wdh_fein = 3
suchbereich_fein = 4 # in stufen +- um stoer E in feiner skala


E_vals_test = np.array([ 0.031622777, 0.31622777, 10.]).tolist()
E_vals_test_repeated = np.tile(E_vals_test,num_spots).tolist()
spooots_test = np.repeat(spots,len(E_vals_test)).tolist()
szenen_test = [{"ID":-(i+1), "Zeit":"Abend", "Spot":s, "Farbe":"W1", "E":e} for i,(s,e) in enumerate(zip(spooots_test,E_vals_test_repeated))]

def erzeuge_test_durchgang():
    durchgang = {"ID":-1, "Diffus": False, "Zeit": "Abend"}
    durchgang["Szenen"] = rng.permutation(szenen_test).tolist()
    with open("TestDurchgang.txt","w") as file:
            file.write(printer.pformat(durchgang))

def erzeuge_lern_proband():
    proband = {"ID": -1, "Abstufung":'lernen'}
    durchgang = {"ID":-1, "Diffus": False, "Zeit": "Abend"}
    durchgang["Szenen"] = rng.permutation(szenen_test).tolist()
    proband["Durchgange"] = [durchgang]
    with open("ProbandLernen.txt","w") as file:
            file.write(printer.pformat(proband))

def erzeuge_durchgange_diffus(proband_id,nr_wdh,szenen_abend,szenen_nacht):
    durchgange_diffus = []
    for zeit in ["Abend", "Nacht"] if proband_id & 1 else ["Nacht", "Abend"]:
        for w in range(1, nr_wdh+1):
            duchgang_id = 1 + (zeit == "Nacht") # 1,2
            durchgang = {"ID":duchgang_id, "Wiederholung":w, "Diffus": True, "Zeit": zeit}
            durchgang["Szenen"] = rng.permutation(szenen_abend if zeit == "Abend" else szenen_nacht).tolist()
            durchgange_diffus.append(durchgang)
    return durchgange_diffus

def erzeuge_durchgange_spots(proband_id,nr_wdh,szenen_abend,szenen_nacht):
    durchgange_spots = []
    for zeit in ["Abend", "Nacht"] if proband_id & 1 else ["Nacht", "Abend"]:
        for w in range(1, nr_wdh+1):
            duchgang_id = 3 + (zeit == "Nacht") # 3,4
            szenen = rng.permutation(szenen_abend if zeit == "Abend" else szenen_nacht).tolist()
            # erste Hälfte der Szenen
            durchgang1 = {"ID": duchgang_id, "Wiederholung":w, "Diffus": False, "Zeit": zeit}
            durchgang1["Szenen"] = szenen[:len(szenen)//2]
            durchgange_spots.append(durchgang1)
            
            durchgang2 = {"ID":duchgang_id, "Wiederholung":w, "Diffus": False, "Zeit": zeit}
            durchgang2["Szenen"]  = szenen[len(szenen)//2:]
            durchgange_spots.append(durchgang2)
    return durchgange_spots

# grob enthält test-run mit 
def erzeuge_probanden_grob(nr_probanden):
    for proband_id in range(1, nr_probanden+1): 
        proband = {"ID": proband_id, "Abstufung":'grob', "Lerndurchgang": False}
        durchgange_spots = erzeuge_durchgange_spots(proband_id,nr_wdh_grob, szenen_spots_abend_grob, szenen_spots_nacht_grob)
        durchgange_diffus = erzeuge_durchgange_diffus(proband_id,nr_wdh_grob, szenen_diffus_abend_grob, szenen_diffus_nacht_grob)
        if proband_id & 2: # start with diffus
            proband["Durchgange"] = durchgange_spots + durchgange_diffus
        else:
            proband["Durchgange"] = durchgange_diffus + durchgange_spots
        with open("Proband{}_grob.txt".format(proband_id),"w") as file:
            file.write(printer.pformat(proband))

def sliding_window(min_idx, max_idx, middle_idx, window_half_size):
    num = max_idx - min_idx
    window_size = 2 * window_half_size
    high_idx = np.minimum(middle_idx + window_half_size, num - 1)
    low_idx  = high_idx - window_size
    low_idx  = np.maximum(low_idx, 0)
    high_idx  = low_idx + window_size
    return low_idx, high_idx
    
def erzeuge_proband_fein(proband_id, stoer_E_spots_abend, stoer_E_spots_nacht, stoer_E_diffus_abend, stoer_E_diffus_nacht): # stoer_E_grob ist die erste Beleuchtungsstärke die störend war
    proband = {"ID": proband_id, "Abstufung":'fein'}
    # Create Spot Durchgange
    szenen_spots_abend_custom = []
    szenen_spots_nacht_custom = []
    for i in range(num_spots):
        stoer_szene_spots_abend_idx = np.searchsorted(E_stufen_abend, stoer_E_spots_abend[i])
        stoer_szene_spots_nacht_idx = np.searchsorted(E_stufen_nacht, stoer_E_spots_nacht[i])
        spot_offset_abend = i * num_E_stufen_abend
        spot_offset_nacht = i * num_E_stufen_nacht
        spot_abend_low_idx, spot_abend_high_idx = sliding_window(0, num_E_stufen_abend - 1, stoer_szene_spots_abend_idx, suchbereich_fein)
        szenen_spots_abend_custom.extend(szenen_spots_abend[spot_abend_low_idx + spot_offset_abend : spot_abend_high_idx + spot_offset_abend])
        spot_nacht_low_idx, spot_nacht_high_idx = sliding_window(0, num_E_stufen_nacht - 1, stoer_szene_spots_nacht_idx, suchbereich_fein)
        szenen_spots_nacht_custom.extend(szenen_spots_nacht[spot_nacht_low_idx + spot_offset_nacht : spot_nacht_high_idx + spot_offset_nacht])
        
    durchgange_spots = erzeuge_durchgange_spots(proband_id,nr_wdh_fein, szenen_spots_abend_custom, szenen_spots_nacht_custom)
    
    # Create Diffus Durchgange
    stoer_szene_diffus_abend_idx = np.searchsorted(E_stufen_abend, stoer_E_diffus_abend)
    stoer_szene_diffus_nacht_idx = np.searchsorted(E_stufen_nacht, stoer_E_diffus_nacht)
    diffus_abend_low_idx, diffus_abend_high_idx = sliding_window(0, num_E_stufen_abend - 1, stoer_szene_diffus_abend_idx, suchbereich_fein)
    szenen_diffus_abend_custom = szenen_diffus_abend[diffus_abend_low_idx:diffus_abend_high_idx]
    diffus_nacht_low_idx, diffus_nacht_high_idx = sliding_window(0, num_E_stufen_nacht - 1, stoer_szene_diffus_nacht_idx, suchbereich_fein)
    szenen_diffus_nacht_custom = szenen_diffus_nacht[diffus_nacht_low_idx:diffus_nacht_high_idx]
    
    durchgange_diffus = erzeuge_durchgange_diffus(proband_id,nr_wdh_fein, szenen_diffus_abend_custom, szenen_diffus_nacht_custom)
    
    if proband_id & 2: # start with diffus
        proband["Durchgange"] = durchgange_spots + durchgange_diffus
    else:
        proband["Durchgange"] = durchgange_diffus + durchgange_spots
    
    fname = "Proband{}_fein.txt".format(proband_id)
    if os.path.exists(fname):
        print(f"File {fname} already exists. Skipping.")
        return fname
    with open(fname,"w") as file:
        file.write(printer.pformat(proband))
    return fname

if __name__ == "__main__":
    erzeuge_probanden_grob(nr_probanden = 4)

    E_vals_grob = E_vals_fein[::3]
    stoer_E_spots = E_vals_grob[2:6] # for testing the fine generator
    stoer_E_spots = [E_vals_grob[3],E_vals_grob[4],E_vals_grob[3],E_vals_grob[3]]
    erzeuge_proband_fein(1,stoer_E_spots,1)