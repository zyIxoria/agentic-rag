"""
CRAG Knowledge Stripper & Filter.
Phân rã văn bản pháp lý thành các dải tri thức (Knowledge Strips) và lọc bỏ các đoạn nhiễu.
"""

import re
from typing import Any, Dict, List, Tuple
from RAG.retriever.schema import RetrievedChunk
from CRAG.config import crag_config
from CRAG.refinement.schema import KnowledgeStrip, RefinedDocument


class KnowledgeStripper:
    """
    Bộ bóc tách và tinh lọc tri thức pháp lý:
    1. Phân rã văn bản chunk thành các đơn vị tri thức nhỏ (Knowledge Strips - câu, khoản, điểm).
    2. Chấm điểm độ liên quan cục bộ của từng Strip với câu hỏi.
    3. Loại bỏ (Filter out) các strip không đạt ngưỡng STRIP_THRESHOLD.
    4. Bảo tồn tiêu đề điều khoản (Article Heading) để đảm bảo tính chuẩn xác pháp lý.
    """

    def __init__(self, strip_threshold: float = None):
        self.strip_threshold = (
            strip_threshold
            if strip_threshold is not None
            else crag_config.STRIP_THRESHOLD
        )

    def _split_into_strips(self, text: str) -> List[str]:
        """
        Phân tách nội dung chunk thành các đoạn/câu/khoản có cấu trúc.
        Bảo toàn các quy ước văn bản pháp luật:
        - Khoản: '1. ', '2. '
        - Điểm: 'a) ', 'b) '
        - Câu kết thúc bằng dấu chấm xuống dòng hoặc dấu chấm câu.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        raw_strips = []

        for line in lines:
            # Nếu là tiêu đề điều luật (ví dụ: "Điều 125. Áp dụng hình thức...")
            if re.match(r"^Điều\s+\d+", line, re.IGNORECASE):
                raw_strips.append(line)
                continue

            # Tách các khoản/điểm trong dòng nếu có định dạng số thứ tự
            # Ví dụ: "1. Người lao động...", "2. Người sử dụng..."
            sub_clauses = re.split(r"(?=\b\d+\.\s+)", line)
            for clause in sub_clauses:
                clause = clause.strip()
                if not clause:
                    continue
                # Nếu một khoản quá dài (> 200 ký tự) có nhiều câu, phân tách theo câu
                if len(clause) > 250:
                    sentences = re.split(r"(?<=[.!?])\s+", clause)
                    for sent in sentences:
                        sent = sent.strip()
                        if sent:
                            raw_strips.append(sent)
                else:
                    raw_strips.append(clause)

        # Trường hợp văn bản thuần không có xuống dòng
        if not raw_strips:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            raw_strips = [s.strip() for s in sentences if s.strip()]

        return raw_strips

    def _extract_query_tokens(self, query: str) -> List[str]:
        """Trích xuất từ khóa chuyên biệt có ý nghĩa từ truy vấn pháp lý."""
        tokens = re.findall(r"\w+", query.lower())
        # Bộ dừng từ pháp lý bao gồm các từ trung tính và chủ thể phổ quát xuất hiện trong mọi điều khoản
        stopwords = {
            "là", "gì", "thế", "nào", "ở", "đâu", "khi", "nào", "bao", "nhiêu",
            "theo", "quy", "định", "pháp", "luật", "cho", "tôi", "biết", "với",
            "về", "của", "và", "các", "những", "được", "bị", "có", "không", "phải",
            "người", "lao", "động", "người", "sử", "dụng", "thì", "trong", "trường", "hợp",
            "mỗi", "ngày", "năm", "tháng"
        }
        return [t for t in tokens if len(t) > 1 and t not in stopwords]

    def _score_strip(
        self, strip: str, query: str, query_tokens: List[str], chunk_score: float
    ) -> float:
        """
        Tính điểm độ liên quan của từng strip đối với câu hỏi:
        - Heading Điều luật được cộng điểm neo ngữ cảnh.
        - Trùng khớp từ khóa quan trọng và cụm từ.
        - Kết hợp điểm tin cậy gốc của chunk.
        """
        strip_lower = strip.lower()

        # Nếu là tiêu đề Điều luật, luôn giữ điểm neo bảo vệ
        if re.match(r"^Điều\s+\d+", strip, re.IGNORECASE):
            # Nếu số điều xuất hiện trong truy vấn, cực kỳ liên quan
            art_match = re.search(r"điều\s+(\d+)", strip_lower)
            if art_match and art_match.group(1) in query.lower():
                return 1.0
            return 0.75

        # Đếm tỷ lệ token chuyên biệt khớp
        if not query_tokens:
            return chunk_score * 0.5

        matched_tokens = sum(1 for token in query_tokens if token in strip_lower)
        overlap_ratio = matched_tokens / len(query_tokens)

        # Kiểm tra cụm 2 từ (bigrams) liên tiếp từ query (loại trừ từ dừng)
        query_words = [w for w in query.lower().split() if w not in {"người", "lao", "động", "và", "có", "bị"}]
        bigram_bonus = 0.0
        for i in range(len(query_words) - 1):
            bigram = f"{query_words[i]} {query_words[i+1]}"
            if len(bigram) > 5 and bigram in strip_lower:
                bigram_bonus += 0.20

        # Nếu không có từ khóa chuyên biệt nào khớp với nội dung khoản, phạt điểm triệt để
        if matched_tokens == 0 and bigram_bonus == 0:
            return min(0.35, chunk_score * 0.3)

        # Công thức kết hợp: 25% chunk score + 50% token overlap + 25% bigram
        final_score = (
            0.25 * chunk_score + 0.50 * overlap_ratio + min(0.25, bigram_bonus)
        )
        return min(1.0, max(0.0, final_score))

    def refine_chunk(
        self, chunk: RetrievedChunk, query: str, source_index: int
    ) -> RefinedDocument:
        """
        Thực hiện phân rã (decompose), chấm điểm (strip scoring) và lọc (filter)
        cho một RetrievedChunk đơn lẻ.
        """
        raw_strips = self._split_into_strips(chunk.content)
        query_tokens = self._extract_query_tokens(query)

        knowledge_strips: List[KnowledgeStrip] = []
        heading_strip: KnowledgeStrip = None

        for idx, text_strip in enumerate(raw_strips):
            score = self._score_strip(
                text_strip, query, query_tokens, chunk.score
            )
            is_heading = bool(re.match(r"^Điều\s+\d+", text_strip, re.IGNORECASE))
            is_retained = (score >= self.strip_threshold) or is_heading

            ks = KnowledgeStrip(
                strip_id=f"{chunk.chunk_id}_s{idx+1}",
                chunk_id=chunk.chunk_id,
                content=text_strip,
                score=round(score, 4),
                is_retained=is_retained,
                source_index=source_index,
                metadata={
                    "is_heading": is_heading,
                    "document_id": chunk.metadata.get("document_id"),
                    "article_number": chunk.metadata.get("article_number"),
                },
            )
            knowledge_strips.append(ks)
            if is_heading and heading_strip is None:
                heading_strip = ks

        # Thu thập các strip được giữ lại
        retained = [s for s in knowledge_strips if s.is_retained]

        # Bảo vệ: Nếu không có strip nội dung nào vượt ngưỡng nhưng chunk có score tốt (>= 0.65)
        # Giữ lại strip có điểm cao nhất để tránh làm rỗng thông tin
        content_strips = [
            s for s in knowledge_strips if not s.metadata.get("is_heading")
        ]
        if not [s for s in retained if not s.metadata.get("is_heading")]:
            if content_strips:
                best_strip = max(content_strips, key=lambda s: s.score)
                best_strip.is_retained = True
                retained.append(best_strip)

        # Sắp xếp theo thứ tự xuất hiện ban đầu
        retained_sorted = sorted(
            [s for s in knowledge_strips if s.is_retained],
            key=lambda s: int(s.strip_id.split("_s")[-1]),
        )

        refined_content = "\n".join(s.content for s in retained_sorted)
        retained_count = len(retained_sorted)
        discarded_count = len(knowledge_strips) - retained_count

        return RefinedDocument(
            chunk_id=chunk.chunk_id,
            source_index=source_index,
            original_content=chunk.content,
            refined_content=refined_content,
            strips=knowledge_strips,
            metadata=chunk.metadata,
            retained_strips_count=retained_count,
            discarded_strips_count=discarded_count,
        )
