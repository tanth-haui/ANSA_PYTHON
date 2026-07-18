import math
import time
from ansa import base
from ansa import constants

# ==============================================================================
# CẤU HÌNH KIỂM TRA MẮT MESH 2 ĐẦU MÚT (WELD END-TIP QUALITY QC)
# ==============================================================================
WELD_PID = 1              # ID của Property chứa vách đứng Arc
CHECK_PART_NAME = "QC_FAILED_WELD_END_ELEMENTS"

# Tiêu chuẩn mesh tại mút hàn (Vùng khoanh đỏ)
MIN_LENGTH = 4.8
MAX_LENGTH = 5.2

# Sử dụng bình phương khoảng cách để tăng tốc độ so sánh
MIN_LEN_SQ = MIN_LENGTH ** 2
MAX_LEN_SQ = MAX_LENGTH ** 2


# ==============================================================================
# HÀM HỖ TRỢ (UTILITIES)
# ==============================================================================
def get_node_coords(deck, node):
    """Truy xuất tọa độ vị trí thực tế X, Y, Z của Node."""
    try:
        coord = base.GetEntityCardValues(deck, node, ("X", "Y", "Z"))
        if not coord:
            coord = base.GetEntityCardValues(deck, node, ("X1", "X2", "X3"))
            return (coord["X1"], coord["X2"], coord["X3"])
        return (coord["X"], coord["Y"], coord["Z"])
    except Exception:
        return None

def calc_dist_squared(p1, p2):
    """Tính bình phương khoảng cách 3D."""
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2


# ==============================================================================
# HÀM XỬ LÝ NGHIỆP VỤ (BUSINESS LOGIC)
# ==============================================================================
def get_weld_elements(deck, weld_pid):
    """Nhiệm vụ 1: Thu thập tất cả các phần tử mesh thuộc dải hàn Arc."""
    weld_property = base.GetEntity(constants.NASTRAN, "PSHELL", weld_pid)
    if not weld_property:
        print(f"[ERROR]: PSHELL Property ID {weld_pid} does not exist.")
        return []

    weld_shells = base.CollectEntities(deck, weld_property, ["SHELL", "CQUAD4", "CTRIA3"])
    if not weld_shells:
        print(f"[ERROR]: No mesh elements found under Weld PID {weld_pid}.")
        return []
    
    return weld_shells


def find_end_edge_nodes(deck, weld_shells):
    """Nhiệm vụ 2: Tìm chính xác các Node ở 2 đầu mút ngoài cùng ."""
    edge_count = {}
    weld_shells_set = set(weld_shells)

    for shell in weld_shells:
        try:
            nodes = base.CollectEntities(deck, shell, "GRID")
            num_nodes = len(nodes)
            if num_nodes in (3, 4):
                node_ids = [n._id for n in nodes]
                edges = [
                    tuple(sorted((node_ids[i], node_ids[(i + 1) % num_nodes])))
                    for i in range(num_nodes)
                ]
                for edge in edges:
                    edge_count[edge] = edge_count.get(edge, 0) + 1
        except Exception:
            pass

    free_edges = [edge for edge, count in edge_count.items() if count == 1]
    
    free_nodes = set()
    for edge in free_edges:
        n1 = base.GetEntity(constants.NASTRAN, "GRID", edge[0])
        n2 = base.GetEntity(constants.NASTRAN, "GRID", edge[1])
        if n1: free_nodes.add(n1)
        if n2: free_nodes.add(n2)

    node_to_elem_map = base.NodesToElements(list(free_nodes))
    end_nodes = set()

    for node, elems in node_to_elem_map.items():
        arc_count = sum(1 for e in elems if e in weld_shells_set)
        if arc_count == 1:
            end_nodes.add(node)

    return list(end_nodes)


def get_target_evaluation_elements(end_nodes, weld_shells):
    """Nhiệm vụ 3: Tìm các phần tử bám dính xung quanh node mút và loại bỏ chính dải Arc."""
    node_to_elem_map = base.NodesToElements(end_nodes)
    attached_elements = set()
    for elems in node_to_elem_map.values():
        attached_elements.update(elems)

    weld_shells_set = set(weld_shells)
    eval_elements = [e for e in attached_elements if e not in weld_shells_set]
    return eval_elements


def check_element_quality(deck, elem):
    """Nhiệm vụ 4.1: Logic kiểm tra chi tiết từng mắt mesh (QUAD & Kích thước)."""
    try:
        nodes = base.CollectEntities(deck, elem, "GRID")

        if len(nodes) != 4:
            return False, "Not a QUAD element"

        coords = [get_node_coords(deck, n) for n in nodes]
        if any(c is None for c in coords):
            return False, "Error reading node coordinates"

        for i in range(4):
            p1 = coords[i]
            p2 = coords[(i + 1) % 4]
            dist_sq = calc_dist_squared(p1, p2)

            if not (MIN_LEN_SQ <= dist_sq <= MAX_LEN_SQ):
                actual_length = math.sqrt(dist_sq)
                return False, f"Bad edge length: {actual_length:.3f} mm"

        return True, "OK"
    except Exception as e:
        return False, str(e)


def evaluate_all_elements(deck, eval_elements):
    """Nhiệm vụ 4.2: Duyệt qua toàn bộ phần tử mục tiêu và trả về danh sách phần tử lỗi."""
    bad_elements = []
    valid_etypes = {"SHELL", "CTRIA3", "CQUAD4", "N_CTRIA3", "N_CQUAD4"}
    
    for elem in eval_elements:
        etype = base.GetEntityType(deck, elem)
        if etype not in valid_etypes:
            continue

        is_ok, msg = check_element_quality(deck, elem)
        if not is_ok:
            bad_elements.append(elem)
            
    return bad_elements


def isolate_and_store_bad_elements(bad_elements, part_name):
    """Nhiệm vụ 5: Đưa phần tử lỗi vào một Part mới để dễ quản lý và hiển thị lên màn hình."""
    part = None
    try:
        part = base.NewPart(part_name)
    except Exception:
        try:
            part = base.GetEntity(constants.NASTRAN, "ANSAPART", part_name)
        except Exception:
            pass

    if part:
        try:
            base.SetEntityPart(bad_elements, part)
            print(f"[STATUS]: Moved failed elements to ANSA Part: '{part_name}'")
        except Exception:
            for elem in bad_elements:
                try: 
                    base.SetEntityPart(elem, part)
                except Exception: 
                    pass

    base.Or(bad_elements)
    print("[STATUS]: Isolated failed red-area elements on screen.")


# ==============================================================================
# HÀM ĐIỀU PHỐI CHÍNH (MAIN COORDINATOR)
# ==============================================================================
def main():
    start_time = time.perf_counter()
    deck = base.CurrentDeck()
    print("\n" + "=" * 60)
    print("--- CAE QUALITY CHECK: WELD END-TIP TRANSITION MESH ---")
    print("=" * 60)

    # 1. Lấy phần tử dải hàn Arc
    weld_shells = get_weld_elements(deck, WELD_PID)
    if not weld_shells:
        return

    # 2. Tìm điểm đầu mút
    end_edge_nodes = find_end_edge_nodes(deck, weld_shells)
    print(f"[*] Found {len(end_edge_nodes)} exact corner nodes at the end-tips (Blue Circles).")
    
    if not end_edge_nodes:
        print("[WARNING]: No end-edge nodes identified. Check mesh connections.")
        return

    # 3. Lấy vùng mesh cần kiểm tra
    eval_elements = get_target_evaluation_elements(end_edge_nodes, weld_shells)
    print(f"[*] Total target elements in red areas to check: {len(eval_elements)}")

    # 4. Kiểm tra chất lượng các mắt mesh đó
    bad_elements = evaluate_all_elements(deck, eval_elements)

    # In thống kê
    print("\n" + "-" * 40)
    print("Quality Check Results:")
    print(f" -> Failed elements (Out of Spec / TRIA): {len(bad_elements)} / {len(eval_elements)}")
    print("-" * 40)

    # 5. Xử lý hiển thị
    if bad_elements:
        isolate_and_store_bad_elements(bad_elements, CHECK_PART_NAME)
    else:
        print("\n>>> PERFECT! All mesh elements in red areas are within specification! <<<")

    elapsed = time.perf_counter() - start_time
    print(f"\n[INFO]: Elapsed time: {elapsed:.3f} sec")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()