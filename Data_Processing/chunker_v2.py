"""chunker_v2.py - Legal-Aware Chunker V2 for Vietnamese Legal Documents.

Xây dựng bộ chunker pháp lý thông minh (Legal-Aware Chunker) cho Dataset V2:
1. Tôn trọng triệt để cấu trúc lập pháp Việt Nam: Điều -> Khoản -> Điểm.
2. Cấu hình linh hoạt qua ChunkerConfigV2 (target_chunk_tokens, max_chunk_tokens, min_chunk_tokens, overlap_tokens).
3. Loại bỏ triệt để monster chunks (> max_chunk_tokens).
4. Giảm mạnh tỷ lệ micro-chunks (<100 tokens) bằng cơ chế gom Điểm/Khoản liền kề cùng Điều luật.
5. Không bao giờ tạo chunk cụt đầu (headless chunk) chỉ chứa tiêu đề (như "4. Sa thải.").
6. Bảo toàn 100% nội dung (zero text loss) và không ngắt giữa số liệu pháp lý.
7. Đảm bảo 100% Chunk ID là duy nhất và chunk_index tăng tuần tự.
8. Xuất ra đối tượng LegalChunkV2 tuân thủ nghiêm ngặt Pydantic Schema V2.
"""

from __future__ import annotations
import os
import re
import math
import json
import glob
from typing import List, Dict, Any, Optional, Tuple

from Data_Processing.config_v2 import ChunkerConfigV2, DEFAULT_CHUNKER_CONFIG
from Data_Processing.hierarchy_parser import (
    HierarchyParser,
    ParsedDocumentHierarchy,
    ArticleBlock,
    ChapterInfo,
    SectionInfo
)
from Data_Processing.article_parser import (
    ArticleClausePointParser,
    ArticleNode,
    ClauseNode,
    PointNode
)
from Data_Processing.appendix_parser import (
    AppendixParser,
    ParsedLegalUnit
)
from Data_Processing.models_v2 import (
    LegalChunkV2,
    ContentType,
    sanitize_null
)
from Data_Processing.metadata_restorer import (
    DocumentMetadataRestorer,
    DocumentMetadata
)


def split_long_text_safe(
    text: str,
    max_tokens: int,
    overlap_tokens: int,
    config: ChunkerConfigV2,
    context_prefix: str = ""
) -> List[str]:
    r"""Chia nhỏ đoạn văn bản quá dài tại ranh giới câu hợp lệ mà không cắt giữa số liệu pháp lý.
    
    Quy tắc phân tách:
    - Ưu tiên 1: Xuống dòng kép (\n\n) hoặc xuống dòng (\n)
    - Ưu tiên 2: Dấu chấm câu kết thúc mệnh đề: (?<!\d)\.(?!\d)\s+
    - Tuyệt đối không cắt giữa các số liệu: 1.000.000 đồng, 15.5%, ngày 01.01.2021
    - Gối đầu (overlap) theo số lượng câu tương ứng với overlap_tokens
    - Bảo toàn context_prefix (tiêu đề Điều / Lời dẫn Khoản) ở đầu mỗi mảnh nhỏ
    """
    total_tokens = config.count_tokens(text)
    if total_tokens <= max_tokens:
        return [text]

    prefix_tokens = config.count_tokens(context_prefix) if context_prefix else 0
    effective_max = max(config.min_chunk_tokens, max_tokens - prefix_tokens)

    # Tách câu: Không ngắt giữa số thập phân/ngày tháng/tiền tệ
    raw_sentences = re.split(r'(?<=[;\n])\s+|(?<!\d)\.(?!\d)\s+', text)
    sentences = [s.strip() for s in raw_sentences if s.strip()]

    chunks: List[str] = []
    curr_sentences: List[str] = []
    curr_tokens = 0

    for s in sentences:
        s_tokens = config.count_tokens(s)
        
        # Nếu bản thân một câu duy nhất dài hơn effective_max -> cắt theo từ
        if s_tokens > effective_max:
            if curr_sentences:
                body = " ".join(curr_sentences)
                full = f"{context_prefix}\n{body}".strip() if context_prefix else body
                chunks.append(full)
                curr_sentences = []
                curr_tokens = 0
            
            words = s.split()
            w_max = config.tokens_to_words(effective_max)
            w_overlap = config.tokens_to_words(overlap_tokens)
            w_idx = 0
            while w_idx < len(words):
                end_idx = min(len(words), w_idx + w_max)
                sub_body = " ".join(words[w_idx:end_idx])
                full = f"{context_prefix}\n{sub_body}".strip() if context_prefix else sub_body
                chunks.append(full)
                if end_idx >= len(words):
                    break
                w_idx = max(w_idx + 1, end_idx - w_overlap)
            continue

        if curr_sentences and (curr_tokens + s_tokens > effective_max):
            body = " ".join(curr_sentences)
            full = f"{context_prefix}\n{body}".strip() if context_prefix else body
            chunks.append(full)

            # Tạo overlap từ các câu gần nhất của chunk trước
            overlap_sentences: List[str] = []
            ov_tokens = 0
            for prev_s in reversed(curr_sentences):
                p_tok = config.count_tokens(prev_s)
                if ov_tokens + p_tok <= overlap_tokens:
                    overlap_sentences.insert(0, prev_s)
                    ov_tokens += p_tok
                else:
                    break
            curr_sentences = list(overlap_sentences)
            curr_tokens = ov_tokens

        curr_sentences.append(s)
        curr_tokens += s_tokens

    if curr_sentences:
        body = " ".join(curr_sentences)
        full = f"{context_prefix}\n{body}".strip() if context_prefix else body
        chunks.append(full)

    return chunks


class LegalAwareChunkerV2:
    """Bộ chia chunk phân cấp pháp lý V2 (Legal-Aware Chunker V2)."""

    def __init__(self, config: Optional[ChunkerConfigV2] = None):
        self.config = config or DEFAULT_CHUNKER_CONFIG
        self.h_parser = HierarchyParser()
        self.a_parser = ArticleClausePointParser()
        self.app_parser = AppendixParser()
        self.meta_restorer = DocumentMetadataRestorer()

        # Regex phát hiện các hậu tố trích dẫn / tham chiếu
        self.re_ref_suffix = re.compile(
            r'^(?:\s*của\b|\s*này\b|\s*và\b|\s*đến\b|\s*hoặc\b|\s*trừ\b|\s*được\b|\s*là\b|\s*quy\s+định\b|\s*áp\s+dụng\b)',
            re.IGNORECASE
        )

    def _is_citation_article(self, art_node: ArticleNode, art: ArticleBlock) -> bool:
        """Kiểm tra xem một ArticleBlock có phải là dòng trích dẫn dở dang / false heading không.
        
        Tuân thủ nguyên tắc: Article Heading có ưu tiên tuyệt đối trước citation detection.
        Một Điều luật có tiêu đề hợp lệ và/hoặc có các khoản, nội dung thực sự thì KHÔNG BAO GIỜ
        được coi là citation và không bao giờ bị merge vào Điều trước đó.
        """
        # 1. Nếu Article có Khoản hoặc có tiêu đề và nhiều hơn 1 dòng -> ĐÂY LÀ ĐIỀU LUẬT THẬT
        if art_node.clauses or (art_node.article_title and len(art.lines) > 1):
            return False

        first_line = art.lines[0].strip() if art.lines else ''
        m = re.match(r'^(?:Điều|ĐIỀU|điều)\s+\d+\b(.*)$', first_line)
        if m:
            rest = m.group(1).strip()
            # Nếu sau số Điều không có dấu phân cách hợp lệ (. : - – —) mà là từ nối tham chiếu
            # VD: "Điều 169 của Bộ luật Lao động", "Điều 12 Nghị định này"
            if rest and not rest.startswith(('.', ':', '-', '–', '—')):
                if self.re_ref_suffix.match(rest) or rest.startswith(('Nghị định này', 'Bộ luật này', 'Luật này', 'Thông tư này')):
                    return True

        # Mẫu Điều bị rớt dở dang chỉ có vài từ như "Điều 142 ." không có nội dung tiếp theo
        if len(art.lines) <= 2 and self.config.count_tokens("\n".join(art.lines)) < 15:
            if not art_node.article_title and not art_node.clauses:
                return True

        return False

    def _get_clause_full_text(self, clause: ClauseNode) -> str:
        """Tái tạo toàn văn nội dung của một Khoản (bao gồm cả các Điểm nếu có)."""
        if not clause.points:
            return clause.content
        intro = clause.intro_text or clause.content
        pts_text = "\n".join(p.content for p in clause.points)
        if intro:
            return f"{intro}\n{pts_text}"
        return pts_text

    def chunk_document(
        self,
        raw_text: str,
        meta: Optional[Dict[str, Any]] = None,
        doc_id: str = "DOC"
    ) -> List[LegalChunkV2]:
        """Chia chunk hoàn chỉnh cho một văn bản pháp luật theo cấu trúc phân cấp pháp lý."""
        meta = meta or {}
        doc_meta = self.meta_restorer.restore_metadata(meta, raw_text, doc_id)
        doc_hierarchy = self.h_parser.parse(raw_text, document_id=doc_id)

        raw_chunks: List[Dict[str, Any]] = []

        # 1. Chunking phần Điều luật (Articles)
        for art in doc_hierarchy.articles:
            art_node = self.a_parser.parse_article_content(
                article_number=art.number,
                article_title=art.title,
                lines=art.lines,
                chapter_number=art.chapter_number,
                chapter_title=art.chapter_title,
                section_number=art.section_number,
                section_title=art.section_title
            )

            # Nếu là dòng trích dẫn dở dang -> gộp an toàn vào chunk phía trước để không làm mất nội dung
            if self._is_citation_article(art_node, art):
                if raw_chunks:
                    add_text = "\n" + "\n".join(art.lines).strip()
                    cand_tokens = self.config.count_tokens(raw_chunks[-1]["content"] + add_text)
                    if cand_tokens <= self.config.max_chunk_tokens:
                        raw_chunks[-1]["content"] += add_text
                        raw_chunks[-1]["tokens"] = cand_tokens
                        continue
                # Nếu không thể gộp hoặc là chunk đầu, cứ xử lý bình thường để không bao giờ mất text

            art_chunks = self._chunk_article(art_node, doc_id, doc_meta)
            raw_chunks.extend(art_chunks)

        # 2. Chunking phần Phụ lục / Bảng biểu / Biểu mẫu / Danh mục (Appendixes)
        if doc_hierarchy.appendix_lines:
            app_units = self.app_parser.parse_appendix_lines(
                doc_hierarchy.appendix_lines,
                document_id=doc_id,
                document_title=doc_meta.document_title
            )
            for unit in app_units:
                app_chunks = self._chunk_appendix_unit(unit, doc_id, doc_meta)
                raw_chunks.extend(app_chunks)

        # 3. Hậu xử lý (Post-Processing):
        # A. Cắt nhỏ triệt để mọi chunk > max_chunk_tokens bằng split_long_text_safe
        bounded_chunks: List[Dict[str, Any]] = []
        for c in raw_chunks:
            if c["tokens"] > self.config.max_chunk_tokens:
                sub_splits = split_long_text_safe(
                    c["content"],
                    self.config.max_chunk_tokens,
                    self.config.overlap_tokens,
                    self.config
                )
                for s_i, sub_text in enumerate(sub_splits):
                    sub_c = dict(c)
                    sub_c["chunk_id"] = f"{c['chunk_id']}_{s_i+1}"
                    sub_c["content"] = sub_text
                    sub_c["tokens"] = self.config.count_tokens(sub_text)
                    bounded_chunks.append(sub_c)
            else:
                bounded_chunks.append(c)

        # B. Gom các micro-chunks (< 35 tokens) là tiêu đề phụ lục / bảng vào chunk tiếp theo
        consolidated: List[Dict[str, Any]] = []
        idx = 0
        while idx < len(bounded_chunks):
            c = dict(bounded_chunks[idx])
            # Chỉ gom nếu là tiêu đề bảng/mẫu/phụ lục cụt không có thân nội dung
            if c["tokens"] < 35 and c.get("content_type") in (ContentType.TABLE.value, ContentType.FORM.value, ContentType.APPENDIX.value, ContentType.OTHER.value):
                if idx + 1 < len(bounded_chunks) and bounded_chunks[idx + 1]["document_id"] == c["document_id"]:
                    nxt = dict(bounded_chunks[idx + 1])
                    merged_tokens = c["tokens"] + nxt["tokens"]
                    if merged_tokens <= self.config.max_chunk_tokens:
                        nxt["content"] = c["content"] + "\n\n" + nxt["content"]
                        nxt["tokens"] = self.config.count_tokens(nxt["content"])
                        bounded_chunks[idx + 1] = nxt
                        idx += 1
                        continue
            consolidated.append(c)
            idx += 1

        # C. Đảm bảo 100% Unique Chunk IDs và gán chunk_index tuần tự theo TASK DATA-09
        seen_ids: set[str] = set()
        final_chunks: List[LegalChunkV2] = []

        for seq_idx, item in enumerate(consolidated):
            base_id = item["chunk_id"]
            # Định dạng chuẩn: {document_id}_{hierarchy}_{chunk_index}
            unique_id = f"{base_id}_{seq_idx}"
            if unique_id in seen_ids:
                # Cơ chế phòng vệ bổ sung nếu phát hiện trùng lặp bất thường
                collision_count = 1
                while f"{unique_id}_c{collision_count}" in seen_ids:
                    collision_count += 1
                unique_id = f"{unique_id}_c{collision_count}"
            seen_ids.add(unique_id)

            chunk_obj = LegalChunkV2(
                chunk_id=unique_id,
                document_id=doc_id,
                document_number=doc_meta.document_number,
                document_title=doc_meta.document_title,
                document_type=doc_meta.document_type,
                chapter_number=sanitize_null(item.get("chapter_number")),
                chapter_title=sanitize_null(item.get("chapter_title")),
                section_number=sanitize_null(item.get("section_number")),
                section_title=sanitize_null(item.get("section_title")),
                article_number=sanitize_null(item.get("article_number")),
                article_title=sanitize_null(item.get("article_title")),
                clause_number=sanitize_null(item.get("clause_number")),
                point_number=sanitize_null(item.get("point_number")),
                content=item["content"],
                issue_date=doc_meta.issue_date,
                effective_from=doc_meta.effective_from,
                effective_to=doc_meta.effective_to,
                legal_status=doc_meta.legal_status,
                source_url=doc_meta.source_url,
                parent_document=doc_id,
                parent_article=sanitize_null(item.get("parent_article")),
                chunk_index=seq_idx,
                content_type=item.get("content_type", ContentType.ARTICLE.value),
                appendix_number=sanitize_null(item.get("appendix_number")),
                appendix_title=sanitize_null(item.get("appendix_title"))
            )
            final_chunks.append(chunk_obj)

        return final_chunks

    def _chunk_article(
        self,
        art_node: ArticleNode,
        doc_id: str,
        doc_meta: DocumentMetadata
    ) -> List[Dict[str, Any]]:
        """Phân rã Điều luật thành các chunk tuân theo hierarchy Điều -> Khoản -> Điểm."""
        art_chunks: List[Dict[str, Any]] = []
        d_clean = art_node.article_number.replace(' ', '')
        parent_art = f"{doc_id}_{d_clean}"
        heading_prefix = f"{art_node.article_number}. {art_node.article_title}\n" if art_node.article_title else f"{art_node.article_number}\n"

        total_art_content = art_node.content or "\n".join(art_node.raw_lines)
        if not total_art_content.startswith(art_node.article_number):
            full_article_text = heading_prefix + total_art_content
        else:
            full_article_text = total_art_content

        total_tokens = self.config.count_tokens(full_article_text)

        # Trường hợp 1: Điều luật hoàn chỉnh có kích thước <= target_chunk_tokens
        # Giữ trọn vẹn toàn bộ Điều trong một chunk duy nhất (không bị cắt vụn)
        if total_tokens <= self.config.target_chunk_tokens:
            art_chunks.append({
                "chunk_id": f"{parent_art}",
                "document_id": doc_id,
                "document_number": doc_meta.document_number,
                "document_title": doc_meta.document_title,
                "document_type": doc_meta.document_type,
                "chapter_number": art_node.chapter_number,
                "chapter_title": art_node.chapter_title,
                "section_number": art_node.section_number,
                "section_title": art_node.section_title,
                "article_number": art_node.article_number,
                "article_title": art_node.article_title,
                "clause_number": None,
                "point_number": None,
                "content": full_article_text,
                "issue_date": doc_meta.issue_date,
                "effective_from": doc_meta.effective_from,
                "effective_to": doc_meta.effective_to,
                "legal_status": doc_meta.legal_status,
                "source_url": doc_meta.source_url,
                "parent_document": doc_id,
                "parent_article": parent_art,
                "content_type": ContentType.ARTICLE.value,
                "tokens": total_tokens
            })
            return art_chunks

        # Trường hợp 2: Điều luật dài > target_chunk_tokens -> phân rã theo Khoản & Điểm
        clause_units: List[List[Dict[str, Any]]] = []

        for c_idx, clause in enumerate(art_node.clauses):
            c_num = clause.clause_number or (f"Khoản {clause.clause_index}" if len(art_node.clauses) > 1 else None)
            c_clean = (c_num or f"C{c_idx+1}").replace(' ', '')

            # A. Khoản có chứa các Điểm a, b, c...
            if clause.points:
                intro = clause.intro_text or (f"{c_num}." if c_num else "")
                clause_full_text = self._get_clause_full_text(clause)
                c_full_tokens = self.config.count_tokens(clause_full_text)

                # Nếu cả Khoản bao gồm tất cả các Điểm vẫn <= target_chunk_tokens -> Giữ trọn Khoản
                if c_full_tokens <= self.config.target_chunk_tokens:
                    body = f"{heading_prefix}{clause_full_text}"
                    clause_units.append([{
                        "chunk_id": f"{parent_art}_{c_clean}",
                        "clause_num": c_num,
                        "point_num": None,
                        "content": body,
                        "tokens": self.config.count_tokens(body),
                        "content_type": ContentType.CLAUSE.value
                    }])
                else:
                    # Gom nhóm các Điểm (Point Grouping) kèm lời dẫn của Khoản
                    pt_chunks: List[Dict[str, Any]] = []
                    pt_idx = 0
                    pt_grp = 1
                    clause_ctx = f"{heading_prefix}{intro}\n".strip() if self.config.include_intro_context else ""

                    while pt_idx < len(clause.points):
                        group_pts: List[PointNode] = []
                        group_tokens = self.config.count_tokens(clause_ctx)
                        start_letter = clause.points[pt_idx].point_letter
                        end_letter = start_letter

                        while pt_idx < len(clause.points):
                            pt = clause.points[pt_idx]
                            pt_tok = self.config.count_tokens(pt.content)
                            if group_pts and (group_tokens + pt_tok > self.config.target_chunk_tokens) and (group_tokens >= self.config.min_chunk_tokens):
                                break
                            group_pts.append(pt)
                            group_tokens += pt_tok
                            end_letter = pt.point_letter
                            pt_idx += 1
                            if group_tokens >= self.config.max_chunk_tokens:
                                break

                        # Gom các điểm lẻ cuối cùng nếu chúng quá nhỏ (< min_chunk_tokens)
                        if pt_idx < len(clause.points):
                            rem_pts = clause.points[pt_idx:]
                            rem_tok = sum(self.config.count_tokens(p.content) for p in rem_pts)
                            if rem_tok < self.config.min_chunk_tokens and (group_tokens + rem_tok <= self.config.max_chunk_tokens):
                                group_pts.extend(rem_pts)
                                end_letter = rem_pts[-1].point_letter
                                pt_idx = len(clause.points)

                        pt_label = f"Điểm {start_letter}" if start_letter == end_letter else f"Điểm {start_letter} đến {end_letter}"
                        pts_body = "\n".join([p.content for p in group_pts])
                        full_content = f"{clause_ctx}\n{pts_body}".strip() if clause_ctx else pts_body

                        # Nếu điểm đơn lẻ quá dài > max_chunk_tokens -> split an toàn
                        if self.config.count_tokens(full_content) > self.config.max_chunk_tokens:
                            sub_splits = split_long_text_safe(
                                full_content,
                                self.config.max_chunk_tokens,
                                self.config.overlap_tokens,
                                self.config,
                                context_prefix=clause_ctx
                            )
                            for s_i, sub_text in enumerate(sub_splits):
                                pt_chunks.append({
                                    "chunk_id": f"{parent_art}_{c_clean}_P{pt_grp}_{s_i+1}",
                                    "clause_num": c_num,
                                    "point_num": pt_label,
                                    "content": sub_text,
                                    "tokens": self.config.count_tokens(sub_text),
                                    "content_type": ContentType.POINT.value
                                })
                        else:
                            pt_chunks.append({
                                "chunk_id": f"{parent_art}_{c_clean}_P{pt_grp}",
                                "clause_num": c_num,
                                "point_num": pt_label,
                                "content": full_content,
                                "tokens": self.config.count_tokens(full_content),
                                "content_type": ContentType.POINT.value
                            })
                        pt_grp += 1
                    clause_units.append(pt_chunks)

            # B. Khoản không chứa Điểm
            else:
                c_tok = self.config.count_tokens(clause.content)
                if c_tok > self.config.max_chunk_tokens:
                    # Khoản dài vượt trần -> split câu an toàn có overlap
                    sub_splits = split_long_text_safe(
                        clause.content,
                        self.config.max_chunk_tokens,
                        self.config.overlap_tokens,
                        self.config,
                        context_prefix=heading_prefix.strip()
                    )
                    sub_chunks: List[Dict[str, Any]] = []
                    for s_i, sub_text in enumerate(sub_splits):
                        sub_chunks.append({
                            "chunk_id": f"{parent_art}_{c_clean}_{s_i+1}",
                            "clause_num": c_num,
                            "point_num": None,
                            "content": sub_text,
                            "tokens": self.config.count_tokens(sub_text),
                            "content_type": ContentType.CLAUSE.value
                        })
                    clause_units.append(sub_chunks)
                else:
                    clause_units.append([{
                        "chunk_id": f"{parent_art}_{c_clean}",
                        "clause_num": c_num,
                        "point_num": None,
                        "content": clause.content,
                        "tokens": c_tok,
                        "content_type": ContentType.CLAUSE.value,
                        "_can_merge": True
                    }])

        # C. Gom các Khoản ngắn liền kề cùng Điều luật (Adjacent Short Clauses Merging)
        flattened: List[Dict[str, Any]] = []
        i = 0
        while i < len(clause_units):
            unit = clause_units[i]
            if len(unit) == 1 and unit[0].get("_can_merge"):
                curr_clauses = [unit[0]]
                curr_tokens = unit[0]["tokens"]
                while curr_tokens < self.config.min_chunk_tokens and i + 1 < len(clause_units):
                    nxt = clause_units[i + 1]
                    if len(nxt) == 1 and nxt[0].get("_can_merge"):
                        nxt_tok = nxt[0]["tokens"]
                        if curr_tokens + nxt_tok <= self.config.target_chunk_tokens:
                            curr_clauses.append(nxt[0])
                            curr_tokens += nxt_tok
                            i += 1
                        else:
                            break
                    else:
                        break

                if len(curr_clauses) > 1:
                    start_c = curr_clauses[0]["clause_num"]
                    end_c = curr_clauses[-1]["clause_num"]
                    c_label = f"{start_c} đến {end_c}" if (start_c and end_c and start_c != end_c) else (start_c or end_c)
                    body = "\n\n".join([c["content"] for c in curr_clauses])
                    full_body = f"{heading_prefix}{body}".strip()
                    flattened.append({
                        "chunk_id": curr_clauses[0]["chunk_id"],
                        "clause_num": c_label,
                        "point_num": None,
                        "content": full_body,
                        "tokens": self.config.count_tokens(full_body),
                        "content_type": ContentType.CLAUSE.value
                    })
                else:
                    full_body = f"{heading_prefix}{curr_clauses[0]['content']}".strip()
                    flattened.append({
                        "chunk_id": curr_clauses[0]["chunk_id"],
                        "clause_num": curr_clauses[0]["clause_num"],
                        "point_num": None,
                        "content": full_body,
                        "tokens": self.config.count_tokens(full_body),
                        "content_type": ContentType.CLAUSE.value
                    })
                i += 1
            else:
                flattened.extend(unit)
                i += 1

        # D. Xử lý Khoản đuôi ngắn cuối cùng (Trailing Micro-clause)
        if len(flattened) > 1 and flattened[-1]["tokens"] < self.config.min_chunk_tokens:
            last = flattened[-1]
            prev = flattened[-2]
            merged_tokens = prev["tokens"] + last["tokens"]
            if merged_tokens <= self.config.max_chunk_tokens:
                prev["content"] = prev["content"] + "\n\n" + last["content"]
                prev["tokens"] = self.config.count_tokens(prev["content"])
                if last.get("clause_num") and prev.get("clause_num"):
                    prev["clause_num"] = f"{prev['clause_num']}, {last['clause_num']}"
                flattened.pop()

        # E. Bao bọc metadata đầy đủ cho mỗi chunk
        for item in flattened:
            art_chunks.append({
                "chunk_id": item["chunk_id"],
                "document_id": doc_id,
                "document_number": doc_meta.document_number,
                "document_title": doc_meta.document_title,
                "document_type": doc_meta.document_type,
                "chapter_number": art_node.chapter_number,
                "chapter_title": art_node.chapter_title,
                "section_number": art_node.section_number,
                "section_title": art_node.section_title,
                "article_number": art_node.article_number,
                "article_title": art_node.article_title,
                "clause_number": item["clause_num"],
                "point_number": item["point_num"],
                "content": item["content"],
                "issue_date": doc_meta.issue_date,
                "effective_from": doc_meta.effective_from,
                "effective_to": doc_meta.effective_to,
                "legal_status": doc_meta.legal_status,
                "source_url": doc_meta.source_url,
                "parent_document": doc_id,
                "parent_article": parent_art,
                "content_type": item["content_type"],
                "tokens": item["tokens"]
            })

        return art_chunks

    def _chunk_appendix_unit(
        self,
        unit: ParsedLegalUnit,
        doc_id: str,
        doc_meta: DocumentMetadata
    ) -> List[Dict[str, Any]]:
        """Phân rã một đơn vị phụ lục/bảng biểu/biểu mẫu thành các chunk đạt chuẩn cấu hình."""
        chunks: List[Dict[str, Any]] = []
        u_tokens = self.config.count_tokens(unit.content)
        header_prefix = f"{unit.appendix_number or ''} {unit.appendix_title or ''}".strip()
        if header_prefix:
            header_prefix += "\n"

        if u_tokens <= self.config.max_chunk_tokens:
            chunks.append({
                "chunk_id": unit.unit_id,
                "document_id": doc_id,
                "document_number": doc_meta.document_number,
                "document_title": doc_meta.document_title,
                "document_type": doc_meta.document_type,
                "chapter_number": None,
                "chapter_title": None,
                "section_number": None,
                "section_title": None,
                "article_number": None,
                "article_title": None,
                "clause_number": None,
                "point_number": None,
                "content": unit.content,
                "issue_date": doc_meta.issue_date,
                "effective_from": doc_meta.effective_from,
                "effective_to": doc_meta.effective_to,
                "legal_status": doc_meta.legal_status,
                "source_url": doc_meta.source_url,
                "parent_document": doc_id,
                "parent_article": None,
                "content_type": unit.content_type,
                "appendix_number": unit.appendix_number,
                "appendix_title": unit.appendix_title,
                "tokens": u_tokens
            })
        else:
            sub_splits = split_long_text_safe(
                unit.content,
                self.config.max_chunk_tokens,
                self.config.overlap_tokens,
                self.config,
                context_prefix=header_prefix.strip()
            )
            for s_i, sub_text in enumerate(sub_splits):
                sub_tok = self.config.count_tokens(sub_text)
                chunks.append({
                    "chunk_id": f"{unit.unit_id}_{s_i+1}",
                    "document_id": doc_id,
                    "document_number": doc_meta.document_number,
                    "document_title": doc_meta.document_title,
                    "document_type": doc_meta.document_type,
                    "chapter_number": None,
                    "chapter_title": None,
                    "section_number": None,
                    "section_title": None,
                    "article_number": None,
                    "article_title": None,
                    "clause_number": None,
                    "point_number": None,
                    "content": sub_text,
                    "issue_date": doc_meta.issue_date,
                    "effective_from": doc_meta.effective_from,
                    "effective_to": doc_meta.effective_to,
                    "legal_status": doc_meta.legal_status,
                    "source_url": doc_meta.source_url,
                    "parent_document": doc_id,
                    "parent_article": None,
                    "content_type": unit.content_type,
                    "appendix_number": unit.appendix_number,
                    "appendix_title": unit.appendix_title,
                    "tokens": sub_tok
                })
        return chunks

    def chunk_corpus(self, raw_dir: str) -> List[LegalChunkV2]:
        """Chia chunk toàn bộ thư mục văn bản thô (data_corpus_raw)."""
        all_chunks: List[LegalChunkV2] = []
        txt_files = sorted(glob.glob(os.path.join(raw_dir, "*.txt")))

        for txt_path in txt_files:
            fname = os.path.basename(txt_path)
            doc_id = fname.replace(".txt", "")
            meta_path = os.path.join(raw_dir, f"{doc_id}_meta.json")
            meta: Dict[str, Any] = {}
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as mf:
                    meta = json.load(mf)

            with open(txt_path, "r", encoding="utf-8") as tf:
                raw_text = tf.read()

            doc_chunks = self.chunk_document(raw_text, meta=meta, doc_id=doc_id)
            all_chunks.extend(doc_chunks)

        return all_chunks
