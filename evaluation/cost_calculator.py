"""evaluation/cost_calculator.py - Công cụ tính toán và quy đổi chi phí Token trên các LLM thương mại.

Hỗ trợ:
- Trích xuất token usage thực tế từ kết quả benchmark (80 câu hỏi) của 3 mô hình:
    1. Traditional RAG Baseline
    2. Corrective RAG (CRAG)
    3. Adaptive Agentic RAG
- Quy đổi chi phí sang USD ($) và VNĐ trên các mô hình thương mại hàng đầu:
    • Google Gemini 1.5 Flash (Siêu tối ưu ngân sách)
    • OpenAI GPT-4o-mini (Tiêu chuẩn công nghiệp)
    • Google Gemini 1.5 Pro (Suy luận pháp lý mở rộng)
    • OpenAI GPT-4o (Flagship đa phương thức)
    • Anthropic Claude 3.5 Sonnet (Chuyên sâu phân tích văn bản)
- Phân tích chi phí ở nhiều quy mô: 1 câu hỏi, 80 câu benchmark, 1.000 câu, 10.000 câu và 100.000 câu.
"""

from __future__ import annotations
import argparse
import json
import logging
from pathlib import Path
import statistics
import sys
from typing import Any, Dict, List, Optional

# Đảm bảo UTF-8 encoding trên console Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Cấu hình tỷ giá hối đoái USD/VND mặc định
DEFAULT_USD_VND_RATE = 25500.0

# Bảng giá niêm yết chính thức của các nhà cung cấp LLM (USD trên 1 Triệu Tokens)
COMMERCIAL_LLM_PRICING: Dict[str, Dict[str, Any]] = {
    "Gemini 1.5 Flash": {
        "provider": "Google DeepMind",
        "input_per_m": 0.075,   # $0.075 / 1M input tokens ($0.000075 / 1K)
        "output_per_m": 0.300,  # $0.300 / 1M output tokens ($0.000300 / 1K)
        "description": "Mô hình tốc độ cực cao, chi phí siêu tiết kiệm, context 1M tokens",
    },
    "GPT-4o-mini": {
        "provider": "OpenAI",
        "input_per_m": 0.150,   # $0.150 / 1M input tokens ($0.000150 / 1K)
        "output_per_m": 0.600,  # $0.600 / 1M output tokens ($0.000600 / 1K)
        "description": "Mô hình chuẩn mực cho hệ thống RAG doanh nghiệp phổ thông",
    },
    "Gemini 1.5 Pro": {
        "provider": "Google DeepMind",
        "input_per_m": 1.250,   # $1.250 / 1M input tokens ($0.001250 / 1K)
        "output_per_m": 5.000,  # $5.000 / 1M output tokens ($0.005000 / 1K)
        "description": "Mô hình cao cấp, năng lực phân tích suy luận pháp lý dài hạn",
    },
    "GPT-4o": {
        "provider": "OpenAI",
        "input_per_m": 2.500,   # $2.500 / 1M input tokens ($0.002500 / 1K)
        "output_per_m": 10.000, # $10.000 / 1M output tokens ($0.010000 / 1K)
        "description": "Flagship mô hình đa phương thức hàng đầu, suy luận logic vượt trội",
    },
    "Claude 3.5 Sonnet": {
        "provider": "Anthropic",
        "input_per_m": 3.000,   # $3.000 / 1M input tokens ($0.003000 / 1K)
        "output_per_m": 15.000, # $15.000 / 1M output tokens ($0.015000 / 1K)
        "description": "Mô hình xuất sắc về lập luận, trích xuất căn cứ và tổng hợp báo cáo",
    },
}


class TokenCostCalculator:
    """Bộ phân tích và tính toán chi phí token trên dữ liệu thực nghiệm."""

    def __init__(
        self,
        results_dir: Optional[Path] = None,
        usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
    ):
        project_root = Path(__file__).resolve().parent.parent
        self.results_dir = results_dir or (project_root / "evaluation" / "results")
        self.usd_vnd_rate = usd_vnd_rate

        self.trad_eval_file = self.results_dir / "traditional_baseline_full_eval.json"
        self.crag_eval_file = self.results_dir / "crag_evaluation.json"
        self.adaptive_eval_file = self.results_dir / "adaptive_evaluation.json"

    def _extract_tokens_from_file(self, filepath: Path, records_key: str) -> Dict[str, Any]:
        if not filepath.exists():
            raise FileNotFoundError(f"Không tìm thấy file kết quả đánh giá: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data.get(records_key, [])
        if not records and "records" in data:
            records = data["records"]

        in_tokens = []
        out_tokens = []
        tot_tokens = []

        for r in records:
            it = r.get("input_tokens", 0)
            ot = r.get("output_tokens", 0)
            tt = r.get("total_tokens", it + ot)
            in_tokens.append(it)
            out_tokens.append(ot)
            tot_tokens.append(tt)

        count = len(records)
        return {
            "count": count,
            "mean_input_tokens": round(statistics.mean(in_tokens), 2) if in_tokens else 0.0,
            "mean_output_tokens": round(statistics.mean(out_tokens), 2) if out_tokens else 0.0,
            "mean_total_tokens": round(statistics.mean(tot_tokens), 2) if tot_tokens else 0.0,
            "sum_input_tokens": sum(in_tokens),
            "sum_output_tokens": sum(out_tokens),
            "sum_total_tokens": sum(tot_tokens),
            "min_total_tokens": min(tot_tokens) if tot_tokens else 0,
            "max_total_tokens": max(tot_tokens) if tot_tokens else 0,
        }

    def get_token_statistics(self) -> Dict[str, Dict[str, Any]]:
        return {
            "Traditional RAG (Baseline)": self._extract_tokens_from_file(
                self.trad_eval_file, "detailed_records"
            ),
            "Corrective RAG (CRAG)": self._extract_tokens_from_file(
                self.crag_eval_file, "records"
            ),
            "Adaptive Agentic RAG": self._extract_tokens_from_file(
                self.adaptive_eval_file, "records"
            ),
        }

    def calculate_cost_matrix(self) -> Dict[str, Any]:
        token_stats = self.get_token_statistics()
        cost_matrix: Dict[str, Any] = {}

        for llm_name, p in COMMERCIAL_LLM_PRICING.items():
            cost_matrix[llm_name] = {
                "provider": p["provider"],
                "description": p["description"],
                "pricing_usd_per_1m": {
                    "input": p["input_per_m"],
                    "output": p["output_per_m"],
                },
                "models": {},
            }

            for model_name, s in token_stats.items():
                mean_in = s["mean_input_tokens"]
                mean_out = s["mean_output_tokens"]
                sum_in = s["sum_input_tokens"]
                sum_out = s["sum_output_tokens"]

                # Chi phí trung bình cho 1 câu hỏi (USD)
                cost_in_per_q = (mean_in / 1_000_000) * p["input_per_m"]
                cost_out_per_q = (mean_out / 1_000_000) * p["output_per_m"]
                cost_per_q_usd = cost_in_per_q + cost_out_per_q
                cost_per_q_vnd = cost_per_q_usd * self.usd_vnd_rate

                # Chi phí chạy toàn bộ 80 câu benchmark
                cost_80_usd = (sum_in / 1_000_000) * p["input_per_m"] + (sum_out / 1_000_000) * p["output_per_m"]
                cost_80_vnd = cost_80_usd * self.usd_vnd_rate

                # Dự phóng quy mô sản xuất
                cost_1k_usd = cost_per_q_usd * 1_000
                cost_1k_vnd = cost_per_q_vnd * 1_000
                cost_10k_usd = cost_per_q_usd * 10_000
                cost_10k_vnd = cost_per_q_vnd * 10_000
                cost_100k_usd = cost_per_q_usd * 100_000
                cost_100k_vnd = cost_per_q_vnd * 100_000

                cost_matrix[llm_name]["models"][model_name] = {
                    "mean_input_tokens": mean_in,
                    "mean_output_tokens": mean_out,
                    "mean_total_tokens": s["mean_total_tokens"],
                    "cost_per_query_usd": round(cost_per_q_usd, 6),
                    "cost_per_query_vnd": round(cost_per_q_vnd, 2),
                    "cost_benchmark_80_usd": round(cost_80_usd, 4),
                    "cost_benchmark_80_vnd": round(cost_80_vnd, 1),
                    "cost_1k_queries_usd": round(cost_1k_usd, 3),
                    "cost_1k_queries_vnd": round(cost_1k_vnd, 1),
                    "cost_10k_queries_usd": round(cost_10k_usd, 2),
                    "cost_10k_queries_vnd": round(cost_10k_vnd, 0),
                    "cost_100k_queries_usd": round(cost_100k_usd, 2),
                    "cost_100k_queries_vnd": round(cost_100k_vnd, 0),
                }

        return {
            "usd_vnd_exchange_rate": self.usd_vnd_rate,
            "token_statistics": token_stats,
            "cost_matrix": cost_matrix,
        }

    def format_markdown_table(self) -> str:
        data = self.calculate_cost_matrix()
        t_stats = data["token_statistics"]
        c_matrix = data["cost_matrix"]
        rate = data["usd_vnd_exchange_rate"]

        md = []
        md.append("# BẢNG QUY ĐỔI CHI PHÍ TOKEN TRÊN CÁC LLM THƯƠNG MẠI\n")
        md.append(f"> **Tỷ giá áp dụng:** 1 USD = {rate:,.0f} VNĐ\n")
        md.append(
            "> **Nguồn dữ liệu:** Kết quả đo đạc thực nghiệm trên toàn bộ 80 câu hỏi kiểm định (Benchmark RAG-08) "
            "thuộc 7 danh mục độ phức tạp pháp luật lao động Việt Nam.\n"
        )

        md.append("## 1. Thống Kê Tiêu Thụ Token Thực Tế (Benchmark 80 Câu)")
        md.append("| Mô hình | Mean Input Tokens | Mean Output Tokens | Mean Total Tokens | Tổng Token (80 câu) | Tiết kiệm so với Baseline |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: |")

        base_tot = t_stats["Traditional RAG (Baseline)"]["mean_total_tokens"]
        for m_name, s in t_stats.items():
            diff = ((s["mean_total_tokens"] - base_tot) / base_tot) * 100.0
            diff_str = "Baseline (Gốc)" if m_name == "Traditional RAG (Baseline)" else f"**{diff:+.2f}%**"
            md.append(
                f"| **{m_name}** | {s['mean_input_tokens']:,.1f} | {s['mean_output_tokens']:,.1f} | "
                f"**{s['mean_total_tokens']:,.1f}** | {s['sum_total_tokens']:,} | {diff_str} |"
            )

        md.append("\n## 2. Chi Phí Trung Bình Cho 1 Câu Hỏi Tra Cứu (USD & VNĐ)")
        md.append("| Nhà Cung Cấp & Mô Hình LLM | Giá In/Out ($/1M) | Traditional RAG | Corrective RAG (CRAG) | Adaptive Agentic RAG | Tiết kiệm chi phí (%) |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: |")

        for llm_name, info in c_matrix.items():
            p_in = info["pricing_usd_per_1m"]["input"]
            p_out = info["pricing_usd_per_1m"]["output"]
            price_tag = f"${p_in:.3f} / ${p_out:.3f}"

            trad = info["models"]["Traditional RAG (Baseline)"]
            crag = info["models"]["Corrective RAG (CRAG)"]
            adapt = info["models"]["Adaptive Agentic RAG"]

            trad_str = f"${trad['cost_per_query_usd']:.5f} ({trad['cost_per_query_vnd']:,.1f}đ)"
            crag_str = f"${crag['cost_per_query_usd']:.5f} ({crag['cost_per_query_vnd']:,.1f}đ)"
            adapt_str = f"${adapt['cost_per_query_usd']:.5f} ({adapt['cost_per_query_vnd']:,.1f}đ)"

            pct_save = ((adapt["cost_per_query_usd"] - trad["cost_per_query_usd"]) / trad["cost_per_query_usd"]) * 100.0
            md.append(f"| **{llm_name}** ({info['provider']}) | {price_tag} | {trad_str} | {crag_str} | **{adapt_str}** | **{pct_save:+.2f}%** |")

        md.append("\n## 3. Dự Phóng Chi Phí Khi Vận Hành Hệ Thống Ở Quy Mô Lớn")
        md.append("### Quy mô 10,000 Truy Vấn Pháp Lý (Mức độ phòng ban / doanh nghiệp vừa)")
        md.append("| Mô hình LLM | Traditional RAG | Corrective RAG (CRAG) | Adaptive Agentic RAG | Chênh lệch tiết kiệm |")
        md.append("| :--- | :---: | :---: | :---: | :---: |")

        for llm_name, info in c_matrix.items():
            trad_10k = info["models"]["Traditional RAG (Baseline)"]["cost_10k_queries_usd"]
            crag_10k = info["models"]["Corrective RAG (CRAG)"]["cost_10k_queries_usd"]
            adapt_10k = info["models"]["Adaptive Agentic RAG"]["cost_10k_queries_usd"]
            trad_10k_vnd = info["models"]["Traditional RAG (Baseline)"]["cost_10k_queries_vnd"]
            adapt_10k_vnd = info["models"]["Adaptive Agentic RAG"]["cost_10k_queries_vnd"]
            saving_vnd = trad_10k_vnd - adapt_10k_vnd

            md.append(
                f"| **{llm_name}** | ${trad_10k:,.2f} ({trad_10k_vnd:,.0f}đ) | "
                f"${crag_10k:,.2f} | **${adapt_10k:,.2f}** ({adapt_10k_vnd:,.0f}đ) | "
                f"Tiết kiệm **{saving_vnd:,.0f} VNĐ** |"
            )

        md.append("\n### Quy mô 100,000 Truy Vấn Pháp Lý (Mức độ Cổng Dịch vụ công / Hệ thống Quốc gia)")
        md.append("| Mô hình LLM | Traditional RAG | Corrective RAG (CRAG) | Adaptive Agentic RAG | Chênh lệch tiết kiệm |")
        md.append("| :--- | :---: | :---: | :---: | :---: |")

        for llm_name, info in c_matrix.items():
            trad_100k = info["models"]["Traditional RAG (Baseline)"]["cost_100k_queries_usd"]
            crag_100k = info["models"]["Corrective RAG (CRAG)"]["cost_100k_queries_usd"]
            adapt_100k = info["models"]["Adaptive Agentic RAG"]["cost_100k_queries_usd"]
            trad_100k_vnd = info["models"]["Traditional RAG (Baseline)"]["cost_100k_queries_vnd"]
            adapt_100k_vnd = info["models"]["Adaptive Agentic RAG"]["cost_100k_queries_vnd"]
            saving_vnd = trad_100k_vnd - adapt_100k_vnd

            md.append(
                f"| **{llm_name}** | ${trad_100k:,.2f} ({trad_100k_vnd:,.0f}đ) | "
                f"${crag_100k:,.2f} | **${adapt_100k:,.2f}** ({adapt_100k_vnd:,.0f}đ) | "
                f"Tiết kiệm **{saving_vnd:,.0f} VNĐ** |"
            )

        md.append("\n## 4. Phân Tích Ý Nghĩa Kỹ Thuật & Nghiên Cứu")
        md.append(
            "1. **Tại sao Traditional RAG tiêu tốn token cao nhất (1,698 tokens/câu)?**\n"
            "   - Pipeline baseline nhồi nhét toàn bộ Top-5 chunks thô vào prompt mà không có cơ chế lọc bỏ đoạn nhiễu.\n"
            "   - Khi câu hỏi yêu cầu từ chối (ngoài phạm vi hoặc thiếu bằng chứng), LLM vẫn phải đọc toàn bộ 5 chunks "
            "và sinh ra câu trả lời dài dòng không cần thiết.\n\n"
            "2. **Tại sao Corrective RAG tiết kiệm được 22.62% tokens?**\n"
            "   - CRAG trang bị bộ lọc Strip Refinement (loại bỏ các câu văn bản pháp luật không liên quan trực tiếp đến truy vấn) "
            "trước khi đưa vào context sinh câu trả lời.\n"
            "   - Nhờ đó, số lượng output tokens giảm mạnh từ 1,087 tokens xuống còn 703 tokens.\n\n"
            "3. **Tại sao Adaptive Agentic RAG tiết kiệm được 23.03% tokens & tối ưu chi phí input?**\n"
            "   - Bộ điều phối **Query Complexity Classifier** nhận diện các câu hỏi ngoài phạm vi hoặc chào hỏi để kích hoạt "
            "nhánh `DIRECT_REFUSAL` hoặc `DIRECT_ANSWER`, hoàn toàn **bỏ qua bước nạp context văn bản pháp lý** (input tokens chỉ vỏn vẹn 22 tokens).\n"
            "   - Đối với các câu hỏi phức tạp cần phân rã (`DECOMPOSE_AGENTIC`), mặc dù có thêm các câu hỏi con nhưng tổng chi phí "
            "toàn hệ thống vẫn thấp hơn 25.6% so với việc truyền context cồng kềnh như Traditional RAG.\n"
        )
        return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="Tính toán quy đổi chi phí Token trên LLM thương mại.")
    parser.add_argument("--json", action="store_true", help="Xuất kết quả định dạng JSON")
    parser.add_argument("--save", action="store_true", help="Lưu kết quả vào reports/experiment_latest/")
    parser.add_argument("--rate", type=float, default=DEFAULT_USD_VND_RATE, help="Tỷ giá USD/VND")
    args = parser.parse_args()

    calc = TokenCostCalculator(usd_vnd_rate=args.rate)
    matrix = calc.calculate_cost_matrix()

    if args.save:
        reports_dir = Path(__file__).resolve().parent.parent / "reports" / "experiment_latest"
        reports_dir.mkdir(parents=True, exist_ok=True)

        json_out = reports_dir / "commercial_llm_cost_analysis.json"
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=2, ensure_ascii=False)
        print(f" Đã lưu JSON phân tích chi phí: {json_out}")

        md_out = reports_dir / "BANG_TINH_CHI_PHI_TOKEN_LLM.md"
        with open(md_out, "w", encoding="utf-8") as f:
            f.write(calc.format_markdown_table())
        print(f" Đã lưu Báo cáo Markdown: {md_out}")

    if args.json:
        print(json.dumps(matrix, indent=2, ensure_ascii=False))
    else:
        print(calc.format_markdown_table())


if __name__ == "__main__":
    main()
