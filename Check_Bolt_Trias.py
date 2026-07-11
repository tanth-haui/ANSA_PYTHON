import os
import time
from ansa import base
from ansa import constants

# ==========================================================
# CONFIGURATION
# ==========================================================
MIN_BOLT_NODE_COUNT = 10
# ==========================================================
# FIND BOLT RBE2
# ==========================================================
def find_bolts(deck):
    bolts = []
    rbe2s = base.CollectEntities(deck, None, "RBE2")
    if not rbe2s:
        print("No RBE2 found.")
        return bolts
    print("Total RBE2 :", len(rbe2s))
    for rbe2 in rbe2s:
        try:
            nodes = base.CollectEntities(deck, rbe2, "GRID")
            if nodes and len(nodes) >= MIN_BOLT_NODE_COUNT:
                bolts.append(rbe2)
        except:
            pass
    print("Bolt Found :", len(bolts))
    return bolts
# ==========================================================
# MAIN
# ==========================================================
def main():
    # ----- Start Timer -----
    start_time = time.perf_counter()
    deck = base.CurrentDeck()
    bolts = find_bolts(deck)
    if not bolts:
        return
    to_display = set()
    for bolt in bolts:
        bolt_nodes = base.CollectEntities(deck, bolt, "GRID")
        if not bolt_nodes:
            continue
        node_map = base.NodesToElements(bolt_nodes)
        if not node_map:
            continue
        checked = set()
        for node_obj, elements_list in node_map.items():
            if not elements_list:
                continue
            for elem in elements_list:
                if elem in checked:
                    continue
                checked.add(elem)
                try:
                    elem_nodes = base.CollectEntities(deck, elem, "GRID")
                    if not elem_nodes:
                        continue
                    # Chỉ lấy element có đúng 3 node
                    if len(elem_nodes) == 3:
                        to_display.add(elem)
                except:
                    pass
    base.Or(list(to_display))
    # ----- End Timer -----
    elapsed = time.perf_counter() - start_time
    print("=" * 50)
    print("Bolt Found      :", len(bolts))
    print("Triangle Found  :", len(to_display))
    print("Elapsed Time    : {:.3f} s".format(elapsed))
    print("=" * 50)
if __name__ == "__main__":
    main()