#!/usr/bin/env python3
"""
누끼 이미지를 각 채널사별 규격에 맞게 자동 리사이징
예시 결과물의 상품 크기/위치와 동일하게 배치
"""

from PIL import Image
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional


CHANNEL_SPECS = {
    'W컨셉': {
        'sizes': [(960, 1280)],
        'example_path': 'W컨셉/BAG',
        'output_path': '썸네일/W컨셉/BAG',
        'has_color_folder': False,
    },
    '자사몰,29CM,HAGO,EQL': {
        'sizes': [(1200, 1200), (1200, 1500)],
        'example_path': '자사몰,29CM,HAGO,EQL/BAG',
        'output_path': '썸네일/자사몰,29CM,HAGO,EQL/BAG',
        'has_color_folder': True,
    },
    '무신사': {
        'sizes': [(1500, 1800)],
        'example_path': '무신사',
        'output_path': '썸네일/무신사',
        'has_color_folder': True,
    },
    '코오롱몰': {
        'sizes': [(1500, 2250)],
        'example_path': '코오롱몰/BAG',
        'output_path': '썸네일/코오롱몰/BAG',
        'has_color_folder': True,
    },
}


def remove_white_background(image):
    """흰색 배경을 투명하게 변환"""
    img = image.convert('RGBA')
    pixels = np.array(img)
    white_mask = (pixels[:, :, 0] > 240) & (pixels[:, :, 1] > 240) & (pixels[:, :, 2] > 240)
    pixels[white_mask, 3] = 0
    return Image.fromarray(pixels, 'RGBA')


def analyze_product_position(img):
    """이미지에서 상품의 크기와 위치를 분석"""
    transparent = remove_white_background(img)
    arr = np.array(transparent)

    product_mask = arr[:, :, 3] > 200
    coords = np.argwhere(product_mask)

    if len(coords) == 0:
        return None

    min_y, min_x = coords.min(axis=0)
    max_y, max_x = coords.max(axis=0)

    return {
        'x': int(min_x),
        'y': int(min_y),
        'width': int(max_x - min_x + 1),
        'height': int(max_y - min_y + 1),
    }


def get_example_files_with_positions(example_product_path: Path, target_size: Tuple[int, int]) -> Dict[str, Dict]:
    """예시 폴더에서 파일명과 상품 위치를 함께 가져오기"""
    result = {}

    # 첫 번째 색상 폴더 찾기 (색상 이름은 무시)
    color_dirs = sorted([d for d in example_product_path.iterdir() if d.is_dir()])
    if not color_dirs:
        return result

    color_dir = color_dirs[0]

    # 파일별 상품 위치 분석
    for file in sorted(color_dir.glob('*.jpg')):
        # 모델컷 제외
        if 'IC' in file.name:
            continue

        img = Image.open(file)
        if img.size != target_size:
            continue

        product_pos = analyze_product_position(img)
        if product_pos:
            result[file.name] = product_pos

    return result


def resize_with_example_position(nuki_img, target_width, target_height, nuki_product_pos, example_product_pos):
    """누끼 이미지를 예시의 상품 위치에 맞게 리사이징"""
    if not nuki_product_pos or not example_product_pos:
        return None

    # 누끼에서 상품 부분 추출
    nuki_transparent = remove_white_background(nuki_img)

    nuki_x = nuki_product_pos['x']
    nuki_y = nuki_product_pos['y']
    nuki_w = nuki_product_pos['width']
    nuki_h = nuki_product_pos['height']
    nuki_aspect = nuki_w / nuki_h if nuki_h > 0 else 1.0

    # 상품 부분 추출
    product_crop = nuki_transparent.crop((nuki_x, nuki_y, nuki_x + nuki_w, nuki_y + nuki_h))

    # 예시의 상품 크기와 위치
    example_x = example_product_pos['x']
    example_y = example_product_pos['y']
    example_w = example_product_pos['width']
    example_h = example_product_pos['height']

    # 누끼의 상품 비율을 유지하면서 예시 높이에 맞추기
    resized_w = int(example_h * nuki_aspect)
    resized_h = example_h

    # 너비가 예시를 벗어나면 예시 너비에 맞추기
    if resized_w > example_w:
        resized_w = example_w
        resized_h = int(resized_w / nuki_aspect)

    # 상품 리사이징
    resized_product = product_crop.resize((resized_w, resized_h), Image.Resampling.LANCZOS)

    # 캔버스 생성
    canvas = Image.new('RGB', (target_width, target_height), 'white')

    # 예시 위치에 배치
    canvas.paste(resized_product, (example_x, example_y), resized_product)

    return canvas


def main():
    print("=" * 80)
    print("상품 이미지 자동 리사이징 시작")
    print("=" * 80)

    nuki_path = Path('누끼 이미지')
    example_path = Path('예시 결과물')
    output_path = Path('★엠디 작업용')

    # 누끼 이미지 폴더에서 상품별 처리
    for product_dir in sorted(nuki_path.iterdir()):
        if not product_dir.is_dir():
            continue

        product_name = product_dir.name
        print(f"\n상품: {product_name}")

        # 색상별 처리
        for color_dir in sorted(product_dir.iterdir()):
            if not color_dir.is_dir():
                continue

            color_name = color_dir.name
            print(f"  색상: {color_name}")

            # 누끼 이미지 파일들
            nuki_images = sorted(color_dir.glob('*.jpg'))
            if not nuki_images:
                continue

            # 첫 번째 누끼 이미지의 상품 위치 분석
            first_nuki = Image.open(nuki_images[0])
            nuki_product_pos = analyze_product_position(first_nuki)

            # 각 채널사별 처리
            for channel_name, channel_info in CHANNEL_SPECS.items():
                example_product_path = example_path / channel_info['example_path'] / product_name

                if not example_product_path.exists():
                    print(f"    {channel_name}: 예시 폴더 없음")
                    continue

                print(f"    {channel_name}:")

                # 각 규격별 처리
                for target_size in channel_info['sizes']:
                    print(f"      {target_size[0]}x{target_size[1]}")

                    # 예시 파일과 상품 위치 가져오기
                    example_files = get_example_files_with_positions(
                        example_product_path,
                        target_size
                    )

                    if not example_files:
                        print(f"        예시 파일 없음")
                        continue

                    # 출력 폴더
                    output_product_path = (
                        output_path /
                        channel_info['output_path'] /
                        product_name /
                        color_name
                    )
                    output_product_path.mkdir(parents=True, exist_ok=True)

                    # 누끼 이미지 리사이징
                    example_filenames = sorted(example_files.keys())
                    for nuki_img_path, example_filename in zip(nuki_images, example_filenames):
                        nuki_img = Image.open(nuki_img_path)

                        # 리사이징 (예시 위치에 맞게)
                        resized = resize_with_example_position(
                            nuki_img,
                            target_size[0],
                            target_size[1],
                            nuki_product_pos,
                            example_files[example_filename]
                        )

                        # 저장
                        if resized:
                            output_file = output_product_path / example_filename
                            resized.save(output_file, 'JPEG', quality=95)
                            print(f"        저장: {output_file.relative_to(output_path)}")

    print("\n" + "=" * 80)
    print("리사이징 완료!")
    print("=" * 80)


if __name__ == '__main__':
    main()
