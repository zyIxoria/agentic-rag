# Terminal: pip install curl_cffi beautifulsoup4
# Terminal: pip install playwright
# Terminal: python -m playwright install chromium
# Terminal: python tvpl_crawler.py

import os
import re
import json
import logging
from typing import Dict
from bs4 import BeautifulSoup, Comment
from playwright.sync_api import sync_playwright

# Cấu hình hệ thống logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TVPL_Crawler")

# Danh sách URL mục tiêu 
TARGET_DOCS = [
    {"id": "BLLD_2019", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx"},
    {"id": "ND_152_2020", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-152-2020-ND-CP-quan-ly-nguoi-lao-dong-nuoc-ngoai-lam-viec-tai-Viet-Nam-280261.aspx"},
    {"id": "ND_145_2020", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-145-2020-ND-CP-huong-dan-Bo-luat-Lao-dong-ve-dieu-kien-lao-dong-quan-he-lao-dong-459400.aspx"},
    {"id": "ND_135_2020", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-135-2020-ND-CP-tuoi-nghi-huu-445512.aspx"},
    {"id": "ND_12_2022", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-12-2022-ND-CP-xu-phat-vi-pham-hanh-chinh-lao-dong-bao-hiem-nguoi-lam-viec-nuoc-ngoai-479312.aspx"},
    {"id": "ND_83_2022", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-83-2022-ND-CP-nghi-huu-o-tuoi-cao-hon-doi-voi-can-bo-cong-chuc-giu-chuc-vu-lanh-dao-532833.aspx"},
    {"id": "ND_70_2023", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-70-2023-ND-CP-sua-doi-Nghi-dinh-152-2020-ND-CP-lao-dong-nuoc-ngoai-579513.aspx"},
    {"id": "ND_74_2024", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-74-2024-ND-CP-muc-luong-toi-thieu-lao-dong-lam-viec-theo-hop-dong-603278.aspx"},
    {"id": "ND_99_2024", "url": "https://thuvienphapluat.vn/van-ban/Bo-may-hanh-chinh/Nghi-dinh-99-2024-ND-CP-sua-doi-diem-p-khoan-1-Dieu-2-Nghi-dinh-83-2022-ND-CP-618974.aspx"},
    {"id": "ND_219_2025", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-219-2025-ND-CP-nguoi-lao-dong-nuoc-ngoai-lam-viec-tai-Viet-Nam-668418.aspx"},
    {"id": "TT_11_2020", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Thong-tu-11-2020-TT-BLDTBXH-Danh-muc-nghe-cong-viec-nang-nhoc-doc-hai-nguy-hiem-464365.aspx"},
    {"id": "TT_10_2020", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Thong-tu-10-2020-TT-BLDTBXH-huong-dan-Bo-luat-Lao-dong-noi-dung-hop-dong-lao-dong-454406.aspx"},
    {"id": "TT_09_2020", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Thong-tu-09-2020-TT-BLDTBXH-huong-dan-Bo-luat-Lao-dong-ve-lao-dong-chua-thanh-nien-466418.aspx"},
    {"id": "TT_20_2023", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Thong-tu-20-2023-TT-BCT-thoi-gio-lam-viec-cong-viec-dac-biet-linh-vuc-tham-do-khai-thac-dau-khi-tren-bien-582969.aspx"},
    {"id": "QD_992_2025", "url": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Quyet-dinh-992-QD-TTg-2025-kien-toan-Hoi-dong-tien-luong-quoc-gia-658031.aspx"}
]

class TVPLPlaywrightScraper:
    def __init__(self, output_dir: str = r"C:\data_corpus_raw"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _clean_text(self, text: str) -> str:
        """Chuẩn hóa chuỗi văn bản: loại bỏ ký tự rác và khoảng trắng dư thừa."""
        if not text:
            return ""
        text = text.replace("\xa0", " ").replace("\ufeff", "").replace("\r", "")
        return re.sub(r"[ \t]+", " ", text).strip()

    def _extract_meta(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Trích xuất metadata (thuộc tính văn bản) từ DOM HTML."""
        meta = {
            "so_hieu": "", "loai_van_ban": "", "co_quan_ban_hanh": "",
            "ngay_ban_hanh": "", "ngay_hieu_luc": "", "tinh_trang_hieu_luc": ""
        }
        info_div = soup.find("div", class_="box-thuoctinh") or soup.find("div", id="divThuocTinh")
        if not info_div:
            return meta
            
        field_map = {
            "số hiệu": "so_hieu", "loại văn bản": "loai_van_ban",
            "ngày ban hành": "ngay_ban_hanh", "ngày có hiệu lực": "ngay_hieu_luc",
            "hiệu lực": "ngay_hieu_luc", "tình trạng": "tinh_trang_hieu_luc"
        }
        for row in info_div.find_all(["tr", "li", "div"]):
            raw = self._clean_text(row.get_text())
            if ":" in raw:
                parts = raw.split(":", 1)
                key, val = parts[0].strip().lower(), parts[1].strip()
                for k, target in field_map.items():
                    if k in key and not meta[target]:
                        meta[target] = val
                        break
        return meta

    def run(self):
        with sync_playwright() as p:
            # Khởi tạo Chromium với cờ vô hiệu hóa AutomationControlled nhằm bypass WAF cơ bản
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            # Cấu hình User-Agent tiêu chuẩn để mô phỏng trình duyệt người dùng
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            success_count = 0
            for doc in TARGET_DOCS:
                doc_id = doc["id"]
                url = doc["url"]
                
                # Kiểm tra cache: Bỏ qua nếu dữ liệu đã tồn tại và đạt dung lượng hợp lệ (>1KB)
                if os.path.exists(os.path.join(self.output_dir, f"{doc_id}.txt")):
                    if os.path.getsize(os.path.join(self.output_dir, f"{doc_id}.txt")) > 1000:
                        logger.info(f"Dữ liệu [{doc_id}] đã tồn tại trong local storage. Bỏ qua.")
                        success_count += 1
                        continue
                
                logger.info(f"Đang tiến hành trích xuất: [{doc_id}]")
                try:
                    page.goto(url, timeout=60000)
                    page.wait_for_timeout(3000)
                    
                    # Cảm biến WAF(Bắt sự kiện Cloudflare Challenge)
                    page_content_str = page.content()
                    if "Verifying you are human" in page_content_str or "Just a moment" in page.title() or "Cloudflare" in page.title():
                        print(f"\n[SYSTEM ALERT] WAF Interception tại: [{doc_id}]")
                        print("Yêu cầu xử lý CAPTCHA thủ công trên trình duyệt.")
                        input("-> Nhấn phím Enter tại đây sau khi DOM tải hoàn tất toàn văn luật: ")
                        page.wait_for_timeout(2000)
                    
                    html_content = page.content()
                    soup = BeautifulSoup(html_content, "html.parser")
                    
                    # Xác thực lại DOM   (  Đảm bảo thoát khỏi vòng lặp WAF)
                    if "Verifying you are human" in soup.get_text():
                        logger.warning(f"Timeout/WAF error tại [{doc_id}]. Hủy quá trình trích xuất tài liệu này.")
                        continue
                    
                    metadata = self._extract_meta(soup)
                    metadata["doc_id"] = doc_id
                    metadata["source"] = url

                    # Truy vấn các container chứa dữ liệu toàn văn bản thường gặp
                    content_div = (
                        soup.find("div", id=re.compile(r"(?i)divContentDoc|toanvan")) 
                        or soup.find("div", class_=re.compile(r"(?i)content1|block-content-law|toanvancontent|content"))
                        or soup.find("article")
                    )
                    
                    # Thuật toán Deep Scan ( Kích hoạt khi cấu trúc DOM không theo chuẩ)n
                    if not content_div:
                        logger.info(f"Kích hoạt Deep Scan (Body parsing) cho [{doc_id}].")
                        content_div = soup.find("body")
                        if not content_div:
                            logger.warning(f"Phân tích DOM thất bại tại [{doc_id}].")
                            continue
                        
                        # Làm sạch các Node cấu trúc (Header, Footer, Navigation)
                        for trash in content_div.find_all(["header", "footer", "nav", "aside"]):
                            trash.decompose()
                        for trash in content_div.select(".header, .footer, .menu, .sidebar, .ads, .box-thuoctinh, .doc-relative"):
                            trash.decompose()

                    # Loại bỏ các Node thực thi (Scripts) và Node ẩn (Styles, Iframes, SVG)
                    for tag in content_div.find_all(["script", "style", "iframe", "noscript", "svg"]):
                        tag.decompose()
                    for comment in content_div.find_all(string=lambda t: isinstance(t, Comment)):
                        comment.extract()
                    for trash in content_div.select("[id*='divQuangCao'], [class*='qc_']"):
                        trash.decompose()

                    lines = []
                    # Trích xuất dữ liệu thô: Duyệt qua các block-level elements và table cells
                    for el in content_div.find_all(["p", "div", "h1", "h2", "h3", "h4", "table", "td"]):
                        if el.name == "div" and el.find(["p", "div", "table"]):
                            continue
                        txt = self._clean_text(el.get_text(separator=" "))
                        if txt and len(txt) > 2 and "thuvienphapluat.vn" not in txt.lower() and "Verifying you are human" not in txt:
                            if not lines or lines[-1] != txt:
                                lines.append(txt)

                    # Lưu trữ Data Corpus và Metadata
                    with open(os.path.join(self.output_dir, f"{doc_id}.txt"), "w", encoding="utf-8") as f:
                        f.write("\n\n".join(lines))
                    with open(os.path.join(self.output_dir, f"{doc_id}_meta.json"), "w", encoding="utf-8") as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)

                    logger.info(f"Process hoàn tất [{doc_id}]: Export {len(lines)} chunks.")
                    success_count += 1

                except Exception as e:
                    logger.error(f"Runtime Exception tại [{doc_id}]: {e}")
            
            browser.close()
            logger.info(f"--- BÁO CÁO HỆ THỐNG: Thành công {success_count}/{len(TARGET_DOCS)} tài liệu ---")

if __name__ == "__main__":
    scraper = TVPLPlaywrightScraper(output_dir=r"C:\data_corpus_raw")
    scraper.run()