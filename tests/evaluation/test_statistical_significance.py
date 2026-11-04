"""
Unit tests for Statistical Significance Analyzer.
"""

import unittest
from evaluation.metrics.statistical_significance import (
    SignificanceAnalyzer,
    StatisticalTestResult,
)


class TestStatisticalSignificance(unittest.TestCase):
    def setUp(self):
        self.analyzer = SignificanceAnalyzer()

    def test_paired_test_computation(self):
        """Kiểm tra tính toán Paired t-test và Wilcoxon với dữ liệu mẫu."""
        records_a = [
            {"question_id": f"q_{i}", "metric": 0.8 + 0.02 * (i % 3)} for i in range(10)
        ]
        records_b = [
            {"question_id": f"q_{i}", "metric": 0.6 + 0.01 * (i % 2)} for i in range(10)
        ]

        res: StatisticalTestResult = self.analyzer.compute_paired_test(
            name="Test Metric",
            path="metric",
            records_a=records_a,
            records_b=records_b,
            name_a="SysA",
            name_b="SysB",
        )

        self.assertEqual(res.n_samples, 10)
        self.assertGreater(res.mean_diff, 0.15)
        self.assertLess(res.p_value_t_test, 0.001)
        self.assertTrue(res.is_significant_p001)
        self.assertGreater(res.cohens_d, 1.0)

    def test_full_comparisons_structure(self):
        """Kiểm tra cấu trúc so sánh toàn diện giữa 3 hệ thống."""
        comparisons = self.analyzer.run_full_comparisons()
        self.assertIn("Adaptive_vs_Baseline", comparisons)
        self.assertIn("Adaptive_vs_CRAG", comparisons)
        self.assertIn("CRAG_vs_Baseline", comparisons)

        results_ab = comparisons["Adaptive_vs_Baseline"]
        self.assertGreater(len(results_ab), 0)
        # Kiểm tra tồn tại metric F1 và latency
        metric_names = [r.metric_name for r in results_ab]
        self.assertIn("Answer Correctness (F1)", metric_names)
        self.assertIn("Total Latency (ms)", metric_names)


if __name__ == "__main__":
    unittest.main()
