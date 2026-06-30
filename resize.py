#!/usr/bin/env python3
"""
원본 이미지를 예시 이미지의 상품 위치/크기에 맞춰 리사이징
배경은 흰색으로 유지
"""

from PIL import Image
import numpy as np
from pathlib import Path


def find_product_bbox(img):
    """이미지에서 상품(비흰색) 영역의 bounding box 찾기"""
    arr = np.array(img.convert('RGB'))
    # 흰색이 아닌 픽셀 찾기 (RGB 각각 245 미만)
    mask = ~((arr[:, :, 0] > 245) & (arr[:, :, 1] > 245) & (arr[:, :, 2] > 245))
    coords = np.argwhere(mask)
    if len(coords) == 0:
        return None
    min_y, min_x = coords.min(axis=0)
    max_y, max_x = coords.max(axis=0)
    return (int(min_x), int(min_y), int(max_x), int(max_y))


def resize_to_match_example(original_img, example_bbox, example_canvas_size):
    """
    원본 이미지를 스케일/이동하여 예시의 상품 위치/크기에 맞춤
    배경은 흰색으로 유지
    """
    original_bbox = find_product_bbox(original_img)
    if original_bbox is None:
        print("  원본에서 상품을 찾을 수 없습니다")
        return None

    orig_x1, orig_y1, orig_x2, orig_y2 = original_bbox
    orig_product_w = orig_x2 - orig_x1
    orig_product_h = orig_y2 - orig_y1

    ex_x1, ex_y1, ex_x2, ex_y2 = example_bbox
    ex_product_w = ex_x2 - ex_x1
    ex_product_h = ex_y2 - ex_y1

    # 상품 크기를 예시에 맞추는 스케일 계산 (비율 유지)
    scale = min(ex_product_w / orig_product_w, ex_product_h / orig_product_h)

    # 원본 이미지 전체를 스케일
    new_w = int(original_img.width * scale)
    new_h = int(original_img.height * scale)
    scaled_img = original_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 스케일된 상품의 위치
    scaled_product_x1 = int(orig_x1 * scale)
    scaled_product_y1 = int(orig_y1 * scale)
    scaled_product_w = int(orig_product_w * scale)
    scaled_product_h = int(orig_product_h * scale)

    # 예시 상품 중심
    ex_center_x = ex_x1 + ex_product_w // 2
    ex_center_y = ex_y1 + ex_product_h // 2

    # 스케일된 상품 중심이 예시 중심에 오도록 오프셋 계산
    offset_x = ex_center_x - (scaled_product_x1 + scaled_product_w // 2)
    offset_y = ex_center_y - (scaled_product_y1 + scaled_product_h // 2)

    # 예시와 동일한 크기의 흰 캔버스 생성
    canvas = Image.new('RGB', example_canvas_size, 'white')
    canvas.paste(scaled_img, (offset_x, offset_y))

    return canvas


def main():
    example_path = Path('example')
    original_path = Path('original')
    work_path = Path('work')

    if not example_path.exists():
        print("❌ example 폴더가 없습니다")
        return
    if not original_path.exists():
        print("❌ original 폴더가 없습니다")
        return

    work_path.mkdir(exist_ok=True)

    # 예시 이미지 분석 (첫 번째 jpg, 하위 폴더 포함)
    example_files = sorted(example_path.rglob('*.jpg'))
    if not example_files:
        print("❌ example 폴더에 jpg 파일이 없습니다")
        return

    example_img = Image.open(example_files[0])
    example_canvas_size = example_img.size
    example_bbox = find_product_bbox(example_img)

    if example_bbox is None:
        print("❌ 예시 이미지에서 상품을 찾을 수 없습니다")
        return

    ex_x1, ex_y1, ex_x2, ex_y2 = example_bbox
    print(f"예시 캔버스 크기: {example_canvas_size[0]}x{example_canvas_size[1]}")
    print(f"예시 상품 위치: x={ex_x1}~{ex_x2}, y={ex_y1}~{ex_y2} (크기: {ex_x2-ex_x1}x{ex_y2-ex_y1})")

    # 원본 이미지 처리 (하위 폴더 포함)
    original_files = sorted(original_path.rglob('*.jpg'))
    if not original_files:
        print("❌ original 폴더에 jpg 파일이 없습니다")
        return

    print(f"\n원본 이미지 처리 중...")
    for original_file in original_files:
        original_img = Image.open(original_file)
        orig_bbox = find_product_bbox(original_img)
        if orig_bbox:
            ox1, oy1, ox2, oy2 = orig_bbox
            print(f"  {original_file.name}: 상품 위치 x={ox1}~{ox2}, y={oy1}~{oy2} (크기: {ox2-ox1}x{oy2-oy1})")

        result = resize_to_match_example(original_img, example_bbox, example_canvas_size)
        if result:
            output_file = work_path / original_file.name
            result.save(output_file, 'JPEG', quality=95)
            print(f"  저장 완료: {output_file}")

    print(f"\n✅ 완료!")


if __name__ == '__main__':
    main()
