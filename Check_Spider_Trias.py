import os
import math
from ansa import base
from ansa import constants

# ==========================================================
# CONFIGURATION
# ==========================================================
TARGET_NODE_COUNT = 9
ZONE_LEVELS = 3      # Attach đến Zone 3
# ==========================================================
# FIND SPIDER RBE2 (9 NODES)
# ==========================================================
def find_spiders(deck):
    spiders = []
    rbe2s = base.CollectEntities(deck, None, "RBE2")
    if not rbe2s:
        print("No RBE2 found.")
        return spiders
    print("Total RBE2 :", len(rbe2s))
    for rbe2 in rbe2s:
        try:
            nodes = base.CollectEntities(deck, rbe2, "GRID")
            if nodes and len(nodes) == TARGET_NODE_COUNT:
                spiders.append(rbe2)
        except:
            pass
    print("Spider Found :", len(spiders))
    return spiders
# ==========================================================
# MAIN
# ==========================================================
def main():
    deck = base.CurrentDeck()
    spiders = find_spiders(deck)
    if not spiders:
        print("No Spider found.")
        return
    # Chỉ hiển thị kết quả cuối
    to_display = set()
    for rbe2 in spiders:
        rbe2_nodes = base.CollectEntities(deck, rbe2, "GRID")
        if not rbe2_nodes:
            continue
        current_frontier_nodes = set(rbe2_nodes)
        all_visited_nodes = set(rbe2_nodes)
        zone3_nodes = set()
        # ==================================================
        # Attach đến Zone 3
        # ==================================================
        for level in range(ZONE_LEVELS):
            next_frontier_nodes = set()
            node_map = base.NodesToElements(list(current_frontier_nodes))
            if not node_map:
                break
            for node_obj, elements_list in node_map.items():
                if not elements_list:
                    continue
                for elem in elements_list:
                    try:
                        elem_nodes = base.CollectEntities(deck, elem, "GRID")
                        if not elem_nodes:
                            continue
                        for n in elem_nodes:
                            if n not in all_visited_nodes:
                                next_frontier_nodes.add(n)
                                all_visited_nodes.add(n)
                    except:
                        pass
            current_frontier_nodes = next_frontier_nodes
            if not current_frontier_nodes:
                break
            # Lưu node ngoài cùng của Zone 3
            if level == ZONE_LEVELS - 1:
                zone3_nodes = set(current_frontier_nodes)
        if not zone3_nodes:
            continue
        # ==================================================
        # Attach thêm 1 lần -> Zone 4
        # ==================================================
        node_map = base.NodesToElements(list(zone3_nodes))
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
                    # Chỉ xét phần tử có 3 node
                    if len(elem_nodes) != 3:
                        continue
                    # Đếm số node nằm trên biên Zone 3
                    count = 0
                    for n in elem_nodes:
                        if n in zone3_nodes:
                            count += 1
                    # Có đúng 2 node thuộc Zone 3
                    if count == 2:
                        to_display.add(elem)
                        to_display.update(elem_nodes)
                except:
                    pass
    if to_display:
        base.All()
        # Show Only kết quả
        base.Invert()
        base.Or(list(to_display))
        print("Triangle found :", len(to_display))
    else:
        print("No matching triangle found.")

if __name__ == "__main__":
    main()