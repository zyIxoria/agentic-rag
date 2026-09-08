import os
import re
import json

def clean_text(text):
    """Làm sạch dữ liệu văn bản thô."""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def hierarchical_chunking(raw_text, van_ban_name, thoi_diem_hieu_luc, doc_id):
    """Sử dụng Regex để thực hiện Hierarchical Chunking theo cấu trúc: Chương, Điều, Khoản."""
    chunks = []
    current_chuong = "Chưa xác định"
    current_dieu = "Chưa xác định"
    current_khoan = "0"
    current_khoan_text = []
    
    # Regex patterns
    regex_chuong = re.compile(r'^(Chương\s+[IVXLCDM]+)\b', re.IGNORECASE)
    regex_dieu = re.compile(r'^(Điều\s+\d+)\.', re.IGNORECASE)
    regex_khoan = re.compile(r'^(\d+)\.\s')

    def save_chunk():
        if current_khoan_text:
            noi_dung = clean_text(" ".join(current_khoan_text))
            if noi_dung:
                # Tạo ID định danh có chứa doc_id để phân biệt giữa các văn bản khác nhau
                id_chunk = f"{doc_id}_{current_chuong.replace(' ', '')}_{current_dieu.replace(' ', '')}_K{current_khoan}"
                
                chunk_data = {
                    "ID_Chunk": id_chunk,
                    "Noi_dung_Chunk": noi_dung,
                    "Van_ban": van_ban_name,
                    "Chuong": current_chuong,
                    "Dieu": current_dieu,
                    "Khoan": current_khoan,
                    "Thoi_diem_hieu_luc": thoi_diem_hieu_luc
                }
                chunks.append(chunk_data)

    lines = raw_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        match_chuong = regex_chuong.match(line)
        if match_chuong:
            save_chunk()
            current_chuong = match_chuong.group(1)
            current_khoan_text = [line]
            current_khoan = "0"
            continue
            
        match_dieu = regex_dieu.match(line)
        if match_dieu:
            save_chunk()
            current_dieu = match_dieu.group(1)
            current_khoan_text = [line]
            current_khoan = "0"
            continue
            
        match_khoan = regex_khoan.match(line)
        if match_khoan:
            save_chunk()
            current_khoan = match_khoan.group(1)
            current_khoan_text = [line]
            continue
            
        current_khoan_text.append(line)
        
    save_chunk()
    return chunks

def process_all_documents(input_dir, output_filepath):
    """Đọc toàn bộ dữ liệu từ folder và xử lý."""
    all_final_chunks = []
    
    if not os.path.exists(input_dir):
        print(f"Lỗi: Không tìm thấy thư mục {input_dir}. Vui lòng kiểm tra lại đường dẫn.")
        return

    print(f"Đang tiến hành đọc dữ liệu từ: {input_dir}...")
    
    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"):
            doc_id = filename.replace(".txt", "")
            txt_path = os.path.join(input_dir, filename)
            meta_path = os.path.join(input_dir, f"{doc_id}_meta.json")
            
            with open(txt_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
                
            van_ban_name = doc_id
            thoi_diem_hieu_luc = "Chưa xác định"
            
            if os.path.exists(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)
                    loai = meta_data.get("loai_van_ban", "")
                    so = meta_data.get("so_hieu", "")
                    if loai or so:
                        van_ban_name = f"{loai} {so}".strip()
                    thoi_diem_hieu_luc = meta_data.get("ngay_hieu_luc", "Chưa xác định")
            
            print(f"- Đang xử lý (Chunking): {van_ban_name}")
            
            chunks = hierarchical_chunking(raw_text, van_ban_name, thoi_diem_hieu_luc, doc_id)
            all_final_chunks.extend(chunks)
            
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(all_final_chunks, f, ensure_ascii=False, indent=4)
        
    print(f"\n=> HOÀN TẤT! Đã gom và chia thành công {len(all_final_chunks)} đoạn (chunks).")
    print(f"=> Dữ liệu đã được lưu tại: {output_filepath}")

if __name__ == "__main__":
    OUTPUT_DIR = "./data_corpus_raw"
    FINAL_JSON = "KhoaLuan_Data_HoanChinh.json"
    
    process_all_documents(OUTPUT_DIR, FINAL_JSON)