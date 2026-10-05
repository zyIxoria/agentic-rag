"""
evaluation/runner/evaluate_classifier.py - Đánh giá định lượng Module 0: Query Complexity Classifier.

Thực hiện:
1. Đánh giá trên Golden Complexity Benchmark (50 câu hỏi phân bố cân bằng 3 lớp + edge cases).
2. Đánh giá trên toàn bộ 80 câu hỏi của Legal QA Benchmark (evaluation/dataset/legal_qa.json).
3. Đo lường:
   - Accuracy, Precision, Recall, F1 theo từng lớp (SIMPLE, MODERATE, COMPLEX)
   - Macro F1
   - Confusion Matrix (3x3)
   - Latency phân loại (mean, median, p95, min, max tính bằng mili-giây)
   - Tỷ lệ lỗi nguy hiểm: Complex-to-Simple Error Rate
   - Determinism consistency (100% tất định qua nhiều lần chạy)
4. Xuất kết quả chi tiết ra evaluation/results/query_complexity_evaluation.json.
"""

import json
import os
import sys
import time
from typing import Dict, List, Any
import numpy as np

# Đảm bảo UTF-8 cho stdout trên Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Đảm bảo import được các module từ root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from Adaptive_RAG.classifier.schema import ComplexityClass, RoutingStrategy
from Adaptive_RAG.classifier.query_complexity_classifier import QueryComplexityClassifier


# =============================================================================
# 1. GOLDEN COMPLEXITY BENCHMARK (50 CÂU HỎI CÓ NHÃN CHUẨN)
# =============================================================================

GOLDEN_BENCHMARK: List[Dict[str, Any]] = [
    # --- 15 CÂU SIMPLE (Đơn vấn đề, định lượng, định nghĩa, đơn điều khoản) ---
    {"id": "SMP_01", "query": "Thời giờ làm việc bình thường của người lao động được quy định tối đa bao nhiêu giờ trong một ngày?", "gold": "SIMPLE"},
    {"id": "SMP_02", "query": "Thời gian nghỉ giữa giờ trong ca làm việc bình thường là bao nhiêu phút?", "gold": "SIMPLE"},
    {"id": "SMP_03", "query": "Tuổi nghỉ hưu của người lao động trong điều kiện lao động bình thường?", "gold": "SIMPLE"},
    {"id": "SMP_04", "query": "Thời hạn của hợp đồng lao động xác định thời hạn tối đa là bao nhiêu tháng?", "gold": "SIMPLE"},
    {"id": "SMP_05", "query": "Mức lương tối thiểu vùng hiện nay do cơ quan nào công bố?", "gold": "SIMPLE"},
    {"id": "SMP_06", "query": "Người lao động được nghỉ bao nhiêu ngày khi kết hôn?", "gold": "SIMPLE"},
    {"id": "SMP_07", "query": "Tiền lương làm việc vào ban đêm được trả thêm ít nhất bao nhiêu phần trăm?", "gold": "SIMPLE"},
    {"id": "SMP_08", "query": "Định nghĩa về quấy rối tình dục tại nơi làm việc trong Bộ luật Lao động?", "gold": "SIMPLE"},
    {"id": "SMP_09", "query": "Hình thức xử lý kỷ luật kéo dài thời hạn nâng lương không quá bao nhiêu tháng?", "gold": "SIMPLE"},
    {"id": "SMP_10", "query": "Điều 125 Bộ luật Lao động 2019 quy định về nội dung gì?", "gold": "SIMPLE"},
    {"id": "SMP_11", "query": "Mức đóng bảo hiểm y tế của người lao động là bao nhiêu phần trăm?", "gold": "SIMPLE"},
    {"id": "SMP_12", "query": "Thời hiệu xử lý kỷ luật lao động tối đa là bao nhiêu tháng?", "gold": "SIMPLE"},
    {"id": "SMP_13", "query": "Hồ sơ đề nghị cấp giấy phép lao động nộp trước bao nhiêu ngày làm việc?", "gold": "SIMPLE"},
    {"id": "SMP_14", "query": "Thời giờ làm việc ban đêm được tính từ mấy giờ đến mấy giờ?", "gold": "SIMPLE"},
    {"id": "SMP_15", "query": "Ai có thẩm quyền công bố mức lương tối thiểu vùng?", "gold": "SIMPLE"},

    # --- 15 CÂU MODERATE (Tình huống, thủ tục, 1-2 điều kiện trong cùng văn bản, CRAG flow) ---
    {"id": "MOD_01", "query": "Người lao động thử việc có được hưởng lương trong thời gian thử việc không?", "gold": "MODERATE"},
    {"id": "MOD_02", "query": "Trình tự, thủ tục các bước tiến hành xử lý kỷ luật sa thải người lao động theo quy định?", "gold": "MODERATE"},
    {"id": "MOD_03", "query": "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước trong trường hợp nào?", "gold": "MODERATE"},
    {"id": "MOD_04", "query": "Thủ tục đăng ký nội quy lao động tại cơ quan chuyên môn về lao động cấp tỉnh gồm những gì?", "gold": "MODERATE"},
    {"id": "MOD_05", "query": "Người lao động có được tạm hoãn thực hiện hợp đồng lao động khi phải thực hiện nghĩa vụ quân sự không?", "gold": "MODERATE"},
    {"id": "MOD_06", "query": "Trong trường hợp người sử dụng lao động không trả lương đúng hạn thì người lao động có quyền gì?", "gold": "MODERATE"},
    {"id": "MOD_07", "query": "Cho em hỏi ad ơi, người lao động bị đuổi việc thì công ty phải báo trước mấy ngày ạ?", "gold": "MODERATE"},
    {"id": "MOD_08", "query": "Điều kiện để người sử dụng lao động được chuyển người lao động làm công việc khác so với hợp đồng lao động?", "gold": "MODERATE"},
    {"id": "MOD_09", "query": "Thời hạn giải quyết quyền lợi của người lao động kể từ ngày chấm dứt hợp đồng lao động?", "gold": "MODERATE"},
    {"id": "MOD_10", "query": "Quy trình xử lý tai nạn lao động tại cơ sở sản xuất kinh doanh gồm các bước nào?", "gold": "MODERATE"},
    {"id": "MOD_11", "query": "Người lao động làm công việc nặng nhọc, độc hại được nghỉ hằng năm tăng thêm bao nhiêu ngày?", "gold": "MODERATE"},
    {"id": "MOD_12", "query": "Thủ tục cấp lại giấy phép lao động cho người lao động nước ngoài hết hạn?", "gold": "MODERATE"},
    {"id": "MOD_13", "query": "Người sử dụng lao động có phải trả sổ bảo hiểm xã hội khi chấm dứt hợp đồng lao động?", "gold": "MODERATE"},
    {"id": "MOD_14", "query": "Người lao động làm việc chưa đủ 12 tháng thì số ngày nghỉ hằng năm tính thế nào?", "gold": "MODERATE"},
    {"id": "MOD_15", "query": "Khi người lao động bị tạm giữ, tạm giam thì hợp đồng lao động có bị chấm dứt không?", "gold": "MODERATE"},

    # --- 15 CÂU COMPLEX (Đa văn bản, viện dẫn chéo, câu hỏi kép đa lĩnh vực, tính toán phức hợp) ---
    {"id": "CPX_01", "query": "Người lao động nữ đang mang thai có được làm thêm giờ vào ban đêm không, và nếu được thì tiền lương được tính như thế nào?", "gold": "COMPLEX"},
    {"id": "CPX_02", "query": "So sánh quy định về thời giờ làm việc và làm thêm giờ giữa Bộ luật Lao động 2019 và Nghị định 145/2020/NĐ-CP?", "gold": "COMPLEX"},
    {"id": "CPX_03", "query": "Người lao động vừa tự ý bỏ việc 5 ngày cộng dồn vừa đang nuôi con nhỏ dưới 12 tháng thì người sử dụng lao động có được áp dụng sa thải không và phải xử lý như thế nào?", "gold": "COMPLEX"},
    {"id": "CPX_04", "query": "Cách tính tiền lương làm thêm giờ vào ban đêm ngày nghỉ lễ tết trùng với ngày nghỉ hằng tuần?", "gold": "COMPLEX"},
    {"id": "CPX_05", "query": "Đối chiếu quy định tại Điều 169 và Điều 219 Bộ luật Lao động 2019 về điều kiện và tuổi nghỉ hưu của lao động nữ?", "gold": "COMPLEX"},
    {"id": "CPX_06", "query": "Mức xử phạt vi phạm hành chính đối với hành vi cưỡng bức lao động theo Nghị định 12/2022 và các trường hợp bị truy cứu trách nhiệm hình sự?", "gold": "COMPLEX"},
    {"id": "CPX_07", "query": "Hồ sơ, thủ tục cấp giấy phép lao động cho chuyên gia nước ngoài theo Nghị định 152/2020 và Nghị định 70/2023 sửa đổi?", "gold": "COMPLEX"},
    {"id": "CPX_08", "query": "Nếu người lao động bị tai nạn lao động suy giảm khả năng lao động 35% thì trách nhiệm bồi thường của người sử dụng lao động và chế độ bảo hiểm xã hội được tính như thế nào?", "gold": "COMPLEX"},
    {"id": "CPX_09", "query": "Trường hợp chấm dứt hợp đồng lao động do thay đổi cơ cấu công nghệ thì quy trình xây dựng phương án sử dụng lao động và mức trợ cấp mất việc làm được tính ra sao?", "gold": "COMPLEX"},
    {"id": "CPX_10", "query": "Người lao động làm công việc đặc biệt nặng nhọc độc hại theo Thông tư 09/2020 thì tuổi nghỉ hưu thấp hơn tối đa bao nhiêu tuổi và mức lương hưu tính theo quy định nào?", "gold": "COMPLEX"},
    {"id": "CPX_11", "query": "Quy định về thời giờ làm việc ban đêm, số giờ làm thêm tối đa và cách tính lương tăng ca cho lao động chưa thành niên?", "gold": "COMPLEX"},
    {"id": "CPX_12", "query": "Điều kiện thành lập tổ chức của người lao động tại doanh nghiệp và quan hệ với tổ chức Công đoàn theo Bộ luật Lao động và các văn bản hướng dẫn?", "gold": "COMPLEX"},
    {"id": "CPX_13", "query": "Nếu doanh nghiệp đơn phương chấm dứt hợp đồng lao động trái pháp luật đối với lao động nữ mang thai thì nghĩa vụ bồi thường gồm những khoản nào và có bị xử phạt theo Nghị định 12/2022 không?", "gold": "COMPLEX"},
    {"id": "CPX_14", "query": "So sánh chế độ bồi thường tai nạn lao động giữa người sử dụng lao động có lỗi và không có lỗi theo Luật ATVSLĐ 2015?", "gold": "COMPLEX"},
    {"id": "CPX_15", "query": "Cách tính tiền trợ cấp thôi việc cho người lao động làm việc từ năm 2005 đến năm 2023 có thời gian đóng bảo hiểm thất nghiệp từ 2009?", "gold": "COMPLEX"},

    # --- 5 CÂU EDGE CASES / NGOÀI PHẠM VI (Out-of-scope / Chào hỏi / Biên) ---
    {"id": "EDG_01", "query": "Xin chào bot, bạn có khỏe không?", "gold": "SIMPLE"},
    {"id": "EDG_02", "query": "Thủ tục đăng ký kết hôn với người nước ngoài tại Sở Tư pháp gồm những giấy tờ gì?", "gold": "SIMPLE"},
    {"id": "EDG_03", "query": "Giá vàng SJC hôm nay bao nhiêu một lượng?", "gold": "SIMPLE"},
    {"id": "EDG_04", "query": "Quy định xử phạt vi phạm nồng độ cồn khi điều khiển xe máy theo Nghị định 100/2019?", "gold": "SIMPLE"},
    {"id": "EDG_05", "query": "Thời tiết Hà Nội tuần này như thế nào?", "gold": "SIMPLE"},
]


def calculate_metrics(gold_labels: List[str], pred_labels: List[str], classes: List[str]) -> Dict[str, Any]:
    """Tính toán Accuracy, Precision, Recall, F1 per class, Macro F1 và Confusion Matrix."""
    total = len(gold_labels)
    correct = sum(1 for g, p in zip(gold_labels, pred_labels) if g == p)
    accuracy = correct / total if total > 0 else 0.0

    # Khởi tạo ma trận nhầm lẫn
    class_idx = {c: i for i, c in enumerate(classes)}
    cm = [[0 for _ in classes] for _ in classes]
    for g, p in zip(gold_labels, pred_labels):
        if g in class_idx and p in class_idx:
            cm[class_idx[g]][class_idx[p]] += 1

    per_class = {}
    f1_list = []
    for c in classes:
        idx = class_idx[c]
        tp = cm[idx][idx]
        fp = sum(cm[r][idx] for r in range(len(classes)) if r != idx)
        fn = sum(cm[idx][c_col] for c_col in range(len(classes)) if c_col != idx)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class[c] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": tp + fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
        f1_list.append(f1)

    macro_f1 = sum(f1_list) / len(f1_list) if f1_list else 0.0

    # Tính Complex-to-Simple Error Rate
    cpx_idx = class_idx["COMPLEX"]
    smp_idx = class_idx["SIMPLE"]
    cpx_to_smp_count = cm[cpx_idx][smp_idx]
    total_complex = sum(cm[cpx_idx])
    cpx_to_smp_rate = (cpx_to_smp_count / total_complex) if total_complex > 0 else 0.0

    return {
        "total_samples": total,
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "complex_to_simple_error_rate": round(cpx_to_smp_rate, 4),
        "complex_to_simple_count": cpx_to_smp_count,
        "per_class": per_class,
        "confusion_matrix": {
            "classes": classes,
            "matrix": cm,
            "interpretation": "Rows are True labels, Columns are Predicted labels"
        }
    }


def main():
    print("=" * 80)
    print("MODULE 0 — QUERY COMPLEXITY CLASSIFIER EVALUATION")
    print("=" * 80)

    classifier = QueryComplexityClassifier()
    classes = ["SIMPLE", "MODERATE", "COMPLEX"]

    # -------------------------------------------------------------------------
    # PART 1: EVALUATION TRÊN GOLDEN COMPLEXITY BENCHMARK (50 SAMPLES)
    # -------------------------------------------------------------------------
    print(f"\n[1/3] Đang chạy đánh giá trên Golden Benchmark ({len(GOLDEN_BENCHMARK)} câu hỏi)...")
    latencies_ms = []
    gold_labels = []
    pred_labels = []
    sample_results = []

    for item in GOLDEN_BENCHMARK:
        start_t = time.perf_counter()
        res = classifier.classify(item["query"])
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        latencies_ms.append(elapsed_ms)

        pred = res.complexity.value
        gold = item["gold"]

        gold_labels.append(gold)
        pred_labels.append(pred)

        sample_results.append({
            "id": item["id"],
            "query": item["query"],
            "gold": gold,
            "predicted": pred,
            "confidence": res.confidence,
            "strategy": res.recommended_strategy.value,
            "is_correct": (gold == pred),
            "reasons": res.reasons,
            "latency_ms": round(elapsed_ms, 3)
        })

    golden_metrics = calculate_metrics(gold_labels, pred_labels, classes)

    latency_stats = {
        "mean_ms": round(float(np.mean(latencies_ms)), 3),
        "median_ms": round(float(np.median(latencies_ms)), 3),
        "p95_ms": round(float(np.percentile(latencies_ms, 95)), 3),
        "min_ms": round(float(np.min(latencies_ms)), 3),
        "max_ms": round(float(np.max(latencies_ms)), 3),
    }

    # -------------------------------------------------------------------------
    # PART 2: DETERMINISTIC CONSISTENCY TEST
    # -------------------------------------------------------------------------
    print("\n[2/3] Kiểm tra tính tất định (Determinism Check x 10 runs)...")
    deterministic_pass = True
    test_queries = [item["query"] for item in GOLDEN_BENCHMARK[:10]]
    for q in test_queries:
        first_res = classifier.classify(q).model_dump()
        for _ in range(9):
            repeat_res = classifier.classify(q).model_dump()
            if first_res["complexity"] != repeat_res["complexity"] or first_res["recommended_strategy"] != repeat_res["recommended_strategy"]:
                deterministic_pass = False
                break

    # -------------------------------------------------------------------------
    # PART 3: EVALUATION TRÊN 80 CÂU HỎI LEGAL_QA.JSON BENCHMARK
    # -------------------------------------------------------------------------
    legal_qa_path = os.path.join(ROOT_DIR, "evaluation", "dataset", "legal_qa.json")
    print(f"\n[3/3] Đang phân tích trên Legal QA Benchmark ({legal_qa_path})...")
    with open(legal_qa_path, "r", encoding="utf-8") as f:
        legal_qa_data = json.load(f)

    legal_qa_results = []
    category_distribution: Dict[str, Dict[str, int]] = {}
    cpx_categories = {"multi_document", "complex_conditions", "cross_reference"}
    cpx_to_simple_in_benchmark = 0

    for q_item in legal_qa_data:
        qid = q_item["question_id"]
        q_text = q_item["question"]
        cat = q_item["category"]

        res = classifier.classify(q_text)
        pred = res.complexity.value

        if cat not in category_distribution:
            category_distribution[cat] = {"SIMPLE": 0, "MODERATE": 0, "COMPLEX": 0, "TOTAL": 0}
        category_distribution[cat][pred] += 1
        category_distribution[cat]["TOTAL"] += 1

        # Kiểm tra nếu category vốn là multi-doc/complex-cond/cross-ref mà bị phân vào SIMPLE
        if cat in cpx_categories and pred == "SIMPLE":
            cpx_to_simple_in_benchmark += 1

        legal_qa_results.append({
            "question_id": qid,
            "category": cat,
            "question": q_text,
            "complexity": pred,
            "strategy": res.recommended_strategy.value,
            "confidence": res.confidence,
            "reasons": res.reasons
        })

    # -------------------------------------------------------------------------
    # TỔNG HỢP VÀ GHI FILE KẾT QUẢ
    # -------------------------------------------------------------------------
    full_output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "classifier_name": "QueryComplexityClassifier",
        "version": "1.0.0",
        "golden_benchmark_metrics": golden_metrics,
        "latency_statistics": latency_stats,
        "determinism_consistency_pass": deterministic_pass,
        "legal_qa_80_analysis": {
            "total_questions": len(legal_qa_data),
            "category_distribution": category_distribution,
            "complex_categories_to_simple_count": cpx_to_simple_in_benchmark,
            "complex_categories_to_simple_rate": round(cpx_to_simple_in_benchmark / sum(category_distribution[c]["TOTAL"] for c in cpx_categories), 4) if cpx_categories else 0.0
        },
        "golden_sample_evaluations": sample_results,
        "legal_qa_sample_evaluations": legal_qa_results
    }

    out_file = os.path.join(ROOT_DIR, "evaluation", "results", "query_complexity_evaluation.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_output, f, ensure_ascii=False, indent=2)

    # In báo cáo tóm tắt ra console
    print("\n" + "=" * 80)
    print("BÁO CÁO KẾT QUẢ ĐÁNH GIÁ QUERY COMPLEXITY CLASSIFIER")
    print("=" * 80)
    print(f"Total Samples (Golden):      {golden_metrics['total_samples']}")
    print(f"Accuracy:                    {golden_metrics['accuracy'] * 100:.2f}%")
    print(f"Macro F1-Score:              {golden_metrics['macro_f1'] * 100:.2f}%")
    print(f"Complex-to-Simple Error Rate: {golden_metrics['complex_to_simple_error_rate'] * 100:.2f}% (Count: {golden_metrics['complex_to_simple_count']})")
    print(f"Deterministic Consistency:   {'PASS (100% tất định)' if deterministic_pass else 'FAIL'}")
    print("-" * 80)
    print("Metrics per class:")
    for c, stats in golden_metrics["per_class"].items():
        print(f"  [{c:8s}] Precision: {stats['precision']*100:6.2f}% | Recall: {stats['recall']*100:6.2f}% | F1: {stats['f1']*100:6.2f}% | Support: {stats['support']}")
    print("-" * 80)
    print("Confusion Matrix (True \\ Pred):")
    print(f"            {'SIMPLE':>10} {'MODERATE':>10} {'COMPLEX':>10}")
    for i, r_name in enumerate(classes):
        row_str = " ".join(f"{golden_metrics['confusion_matrix']['matrix'][i][j]:>10}" for j in range(len(classes)))
        print(f"  {r_name:8s}  {row_str}")
    print("-" * 80)
    print("Latency Statistics:")
    print(f"  Mean:   {latency_stats['mean_ms']:.2f} ms")
    print(f"  Median: {latency_stats['median_ms']:.2f} ms")
    print(f"  P95:    {latency_stats['p95_ms']:.2f} ms")
    print(f"  Min:    {latency_stats['min_ms']:.2f} ms | Max: {latency_stats['max_ms']:.2f} ms")
    print("-" * 80)
    print("Phân phối trên 80 câu hỏi Legal QA Benchmark:")
    for cat, dist in category_distribution.items():
        print(f"  {cat:24s} -> SIMPLE: {dist['SIMPLE']:2d} | MODERATE: {dist['MODERATE']:2d} | COMPLEX: {dist['COMPLEX']:2d} | Total: {dist['TOTAL']:2d}")
    print(f"Complex-to-Simple on Legal QA: {cpx_to_simple_in_benchmark} câu (Rate: {cpx_to_simple_in_benchmark/34*100:.2f}%)")
    print("=" * 80)
    print(f"Kết quả đầy đủ đã lưu tại: {out_file}\n")


if __name__ == "__main__":
    main()
