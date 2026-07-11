import os
import math
from ansa import base
from ansa import constants

# ==========================================================
# CONFIGURATION
# ==========================================================
TARGET_NODE_COUNT = 9
ZONE_LEVELS = 3
DISTANCE_THRESHOLD = 20.0

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
            nodes = base.CollectEntities(
                deck,
                rbe2,
                "GRID"
            )

            if nodes and len(nodes) == TARGET_NODE_COUNT:
                spiders.append(rbe2)
        except:
            continue
    print("Spider Found :", len(spiders))
    return spiders
# ==========================================================
# GET SPIDER CENTER COORDINATES
# ==========================================================
def get_spider_center_coords(deck, rbe2):
    try:
        # Independent node của RBE2
        vals = base.GetEntityCardValues(deck,rbe2,("GN",))
        if not vals or "GN" not in vals:
            return None
        center_node = vals["GN"]
        # GN có thể là ID hoặc Entity
        if isinstance(center_node, int):
            center_node = base.GetEntity(deck, "GRID", center_node)
        if not center_node:
            return None
        # Lấy tọa độ GRID
        coord = base.GetEntityCardValues(deck, center_node, ("X1", "X2", "X3"))
        if coord:
            return (coord["X1"], coord["X2"], coord["X3"])
    except Exception as e:
        print("Center error:", e)
    return None
# ==========================================================
# DISTANCE BETWEEN TWO POINTS
# ==========================================================
def calc_distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
# ==========================================================
# FIND CLOSE SPIDERS
# ==========================================================
def find_close_spiders(spider_centers):
    close_spiders = set()
    spider_list = list(spider_centers.keys())
    print("\nChecking spider distances...")
    for i in range(len(spider_list)):
        for j in range(i+1, len(spider_list)):
            sp1 = spider_list[i]
            sp2 = spider_list[j]
            d = calc_distance(spider_centers[sp1], spider_centers[sp2])
            if d < DISTANCE_THRESHOLD:
                print(
                    "Close Spider distance : {:.3f} mm".format(d)
                )
                close_spiders.add(sp1)
                close_spiders.add(sp2)
    return close_spiders
# ==========================================================
# ATTACH ZONE
# ==========================================================
def attach_zone(deck, rbe2):
    result = set()
    rbe2_nodes = base.CollectEntities(deck, rbe2, "GRID")
    if not rbe2_nodes:
        return result
    current_frontier_nodes = set(rbe2_nodes)
    all_visited_nodes = set(rbe2_nodes)
    for level in range(ZONE_LEVELS):
        next_frontier_nodes = set()
        node_map = base.NodesToElements(list(current_frontier_nodes))
        if not node_map:
            break
        for node_obj, elements_list in node_map.items():
            if not elements_list:
                continue
            result.update(elements_list)
            for elem in elements_list:
                try:
                    elem_nodes = base.CollectEntities(deck, elem, "GRID")
                    for n in elem_nodes:
                        if n not in all_visited_nodes:
                            all_visited_nodes.add(n)
                            next_frontier_nodes.add(n)
                except:
                    continue
        current_frontier_nodes = next_frontier_nodes
        if not current_frontier_nodes:
            break
    return result
# ==========================================================
# MAIN
# ==========================================================
def main():
    deck = base.CurrentDeck()
    spiders = find_spiders(deck)
    if not spiders:
        return
    # ------------------------------------------
    # Get spider centers
    # ------------------------------------------
    spider_centers = {}
    for sp in spiders:
        center = get_spider_center_coords(deck, sp)
        if center:
            spider_centers[sp] = center
    print(
        "Center found :",
        len(spider_centers)
    )
    # ------------------------------------------
    # Find spiders distance < 20mm
    # ------------------------------------------
    close_spiders = find_close_spiders(spider_centers)
    if not close_spiders:
        print(
            "No spider distance < {} mm".format(
                DISTANCE_THRESHOLD
            )
        )
        return
    print("Close Spider Found :", len(close_spiders))
    # ------------------------------------------
    # Attach 3 zones
    # ------------------------------------------
    to_display = set()
    for sp in close_spiders:
        to_display.add(sp)
        mesh = attach_zone(deck, sp)
        to_display.update(mesh)
    base.Or(list(to_display))
    print("Displayed entities :", len(to_display))
if __name__ == "__main__":
    main()