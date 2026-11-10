import zipfile, json, csv, hashlib, os, sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

bundle_dir = Path(__file__).resolve().parent.parent
zip_path = bundle_dir / 'chapter5_evidence_bundle.zip'

print('=== KIỂM TRA TÍNH TOÀN VẸN GÓI BẰNG CHỨNG THỰC NGHIỆM CHƯƠNG 5 (BENCHMARK 300) ===')
if zip_path.exists():
    with zipfile.ZipFile(zip_path, 'r') as zf:
        namelist = zf.namelist()
        print(f'1. Kiểm tra mở ZIP: {len(namelist)} tệp tin.')
        test_res = zf.testzip()
        print(f'   Kiểm tra tính toàn vẹn (CRC32): {"PASS (Không có tệp hỏng)" if test_res is None else f"FAIL: {test_res}"}')
else:
    print('1. Tệp ZIP chưa được tạo.')

print('\n2. Kiểm tra phân tích toàn bộ JSON:')
json_files = sorted(list(bundle_dir.glob('**/*.json')))
for jf in json_files:
    try:
        with open(jf, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cnt = len(data) if isinstance(data, (list, dict)) else 1
        print(f'   - {jf.relative_to(bundle_dir)}: PASS ({cnt} items/keys)')
    except Exception as e:
        print(f'   - {jf.relative_to(bundle_dir)}: FAIL ({e})')

print('\n3. Kiểm tra số dòng các tệp CSV:')
csv_files = sorted(list(bundle_dir.glob('**/*.csv')))
for cf in csv_files:
    with open(cf, 'r', encoding='utf-8') as f:
        reader = list(csv.reader(f))
    print(f'   - {cf.relative_to(bundle_dir)}: {len(reader)-1} rows (header: {len(reader[0])} cols)')

print('\n4. Kiểm tra mã băm checksums.sha256:')
checksum_path = bundle_dir / 'checksums.sha256'
if checksum_path.exists():
    with open(checksum_path, 'r', encoding='utf-8') as f:
        lines = [l.strip().split('  ') for l in f if l.strip()]

    all_match = True
    for expected_hash, rel_path in lines:
        fpath = bundle_dir / rel_path
        if not fpath.exists():
            print(f'   Tệp không tồn tại: {rel_path}')
            all_match = False
            continue
        actual_hash = hashlib.sha256(open(fpath, 'rb').read()).hexdigest()
        if expected_hash != actual_hash:
            print(f'   Lệch mã băm: {rel_path}')
            all_match = False
    print(f'   Kiểm tra {len(lines)} mã băm: {"TẤT CẢ KHỚP 100%" if all_match else "CÓ LỆCH MÃ BĂM!"}')
else:
    print('   Chưa có checksums.sha256.')
