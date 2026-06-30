#!/usr/bin/env python3
"""
누끼 이미지를 각 채널사별 규격에 맞게 자동 리사이징
누끼 이미지의 상품 크기/위치를 그대로 유지하면서 리사이징
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
        'example_path': '무신사/SLG',
        'output_path': '썸네일/무신사/SLG',
        'has_color_folder': False,
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


def crop_product(image):
    """투명한 부분을 제거하고 상품만 남김"""
    bbox = image.getbbox()
    if bbox:
        return image.crop(bbox)
    return image


def analyze_product_position(nuki_img):
    """누끼 이미지에서 상품의 크기와 위치를 분석"""
    # 배경 제거
    transparent = remove_white_background(nuki_img)
    arr = np.array(transparent)

    # 알파값이 200 이상인 부분(상품)만 찾기
    product_mask = arr[:, :, 3] > 200
    coords = np.argwhere(product_mask)

    if len(coords) == 0:
        return None

    min_y, min_x = coords.min(axis=0)
    max_y, max_x = coords.max(axis=0)

    orig_width, orig_height = nuki_img.size

    return {
        'x': int(min_x),
        'y': int(min_y),
        'width': int(max_x - min_x + 1),
        'height': int(max_y - min_y + 1),
        'orig_width': orig_width,
        'orig_height': orig_height,
    }


def resize_to_spec(nuki_img, target_width, target_height, product_position):
    """누끼 이미지의 상품 위치와 크기를 원본 비율로 유지하면서 리사이징"""
    if not product_position:
        return None

    orig_width = product_position['orig_width']
    orig_height = product_position['orig_height']

    # 스케일 계산 (누끼 원본 → 타겟)
    scale_x = target_width / orig_width
    scale_y = target_height / orig_height

    # 누끼 이미지 전체를 타겟 크기로 리사이징
    resized_nuki = nuki_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # 배경 투명화
    resized_transparent = remove_white_background(resized_nuki)

    # 캔버스 생성
    canvas = Image.new('RGB', (target_width, target_height), 'white')

    # 리사이징된 누끼 이미지를 캔버스에 붙이기 (위치 유지)
    canvas.paste(resized_transparent, (0, 0), resized_transparent)

    return canvas


def get_example_filenames(example_product_path: Path, has_color_folder: bool, target_size: Tuple[int, int]) -> list:
    """예시 폴더에서 해당 크기의 파일명 가져오기 (상품 이미지만, 모델컷 제외)"""
    filenames = []

    if has_color_folder:
        # 색상 폴더가 있으면 첫 번째 색상 폴더만 사용
        color_dirs = sorted([d for d in example_product_path.iterdir() if d.is_dir()])
        if not color_dirs:
            return filenames

        first_color_dir = color_dirs[0]
        for file in sorted(first_color_dir.glob('*.jpg')):
            # 모델컷 제외 (IC- 포함된 파일 제외)
            if 'IC' in file.name:
                continue

            # 썸네일 포함
            if '썸네일' in file.name:
                img = Image.open(file)
                if img.size == target_size:
                    filenames.append(file.name)
                continue

            img = Image.open(file)
            if img.size == target_size:
                filenames.append(file.name)
    else:
        for file in sorted(example_product_path.glob('*.jpg')):
            # 모델컷 제외
            if 'IC' in file.name:
                continue

            img = Image.open(file)
            if img.size == target_size:
                filenames.append(file.name)

    return filenames


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

            # 각 누끼 이미지의 상품 위치 분석 (첫 번째만 사용)
            first_nuki = Image.open(nuki_images[0])
            product_position = analyze_product_position(first_nuki)

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

                    # 예시 파일명 가져오기
                    example_filenames = get_example_filenames(
                        example_product_path,
                        channel_info['has_color_folder'],
                        target_size
                    )

                    if not example_filenames:
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
                    for nuki_img_path, example_filename in zip(nuki_images, example_filenames):
                        nuki_img = Image.open(nuki_img_path)

                        # 리사이징
                        resized = resize_to_spec(nuki_img, target_size[0], target_size[1], product_position)

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
