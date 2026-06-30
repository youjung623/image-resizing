#!/usr/bin/env python3
"""
상품 누끼 이미지를 각 채널사별 규격에 맞게 자동 리사이징하는 스크립트
"""

from PIL import Image
import numpy as np
import re
from pathlib import Path
from typing import Dict, List, Tuple


# 채널사별 규격 및 예시 폴더
CHANNEL_SPECS = {
    'W컨셉': {
        'sizes': [(960, 1280)],
        'example_path': 'W컨셉/BAG',
        'output_path': '썸네일/W컨셉/BAG',
        'has_color_folder': False,  # 파일명에 색상 포함
    },
    '자사몰,29CM,HAGO,EQL': {
        'sizes': [(1200, 1200), (1200, 1500)],
        'example_path': '자사몰,29CM,HAGO,EQL/BAG',
        'output_path': '썸네일/자사몰,29CM,HAGO,EQL/BAG',
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
    """이미지에서 흰색 배경을 투명하게 변환"""
    img = image.convert('RGBA')
    pixels = np.array(img)

    # 흰색 배경 감지 및 투명화
    white_mask = (pixels[:, :, 0] > 240) & (pixels[:, :, 1] > 240) & (pixels[:, :, 2] > 240)
    pixels[white_mask, 3] = 0

    return Image.fromarray(pixels, 'RGBA')


def crop_product(image):
    """투명한 부분을 제거하고 상품 부분만 남김"""
    bbox = image.getbbox()
    if bbox:
        return image.crop(bbox)
    return image


def analyze_product_position(example_img):
    """
    예시 이미지에서 상품의 크기와 위치를 분석
    배경이 아닌 픽셀 영역을 찾아 상품의 위치와 크기 반환
    """
    arr = np.array(example_img.convert('RGBA'))

    # 알파 채널 또는 흰색이 아닌 부분 찾기
    if arr.shape[2] == 4:
        # RGBA: 알파값이 200 이상인 부분이 상품
        product_mask = arr[:, :, 3] > 200
    else:
        # RGB: 흰색(240 이상)이 아닌 부분이 상품
        product_mask = ~((arr[:, :, 0] > 240) & (arr[:, :, 1] > 240) & (arr[:, :, 2] > 240))

    coords = np.argwhere(product_mask)

    if len(coords) == 0:
        # 상품을 찾을 수 없으면 중앙 배치
        return None

    min_y, min_x = coords.min(axis=0)
    max_y, max_x = coords.max(axis=0)

    product_x = int(min_x)
    product_y = int(min_y)
    product_width = int(max_x - min_x + 1)
    product_height = int(max_y - min_y + 1)

    img_width, img_height = example_img.size

    return {
        'x': product_x,
        'y': product_y,
        'width': product_width,
        'height': product_height,
        'canvas_width': img_width,
        'canvas_height': img_height,
    }


def resize_to_spec(product_img, target_width, target_height, example_position=None):
    """상품을 지정된 크기의 캔버스에 맞게 리사이징"""
    product_width, product_height = product_img.size

    canvas = Image.new('RGB', (target_width, target_height), 'white')

    if example_position:
        # 예시 이미지의 상품 위치와 크기를 참고
        # 상품이 캔버스에서 차지하는 비율 계산
        ratio_x = example_position['x'] / example_position['canvas_width']
        ratio_y = example_position['y'] / example_position['canvas_height']
        ratio_w = example_position['width'] / example_position['canvas_width']
        ratio_h = example_position['height'] / example_position['canvas_height']

        # 새로운 캔버스에서의 위치 계산
        new_x = int(target_width * ratio_x)
        new_y = int(target_height * ratio_y)
        new_product_width = int(target_width * ratio_w)
        new_product_height = int(target_height * ratio_h)

        # 상품 이미지 리사이징 (예시의 위치와 크기에 맞게)
        resized_product = product_img.resize(
            (new_product_width, new_product_height),
            Image.Resampling.LANCZOS
        )
    else:
        # 예시가 없으면 중앙 배치 (기존 방식)
        width_ratio = target_width / product_width
        height_ratio = target_height / product_height
        scale = min(width_ratio, height_ratio) * 0.95

        new_product_width = int(product_width * scale)
        new_product_height = int(product_height * scale)

        resized_product = product_img.resize(
            (new_product_width, new_product_height),
            Image.Resampling.LANCZOS
        )

        new_x = (target_width - new_product_width) // 2
        new_y = (target_height - new_product_height) // 2

    if resized_product.mode == 'RGBA':
        canvas.paste(resized_product, (new_x, new_y), resized_product)
    else:
        canvas.paste(resized_product, (new_x, new_y))

    return canvas


def get_example_files(example_product_path: Path, has_color_folder: bool) -> Dict[str, List[str]]:
    """
    예시 폴더에서 파일들을 찾아 크기별로 분류
    """
    size_to_files = {}

    if has_color_folder:
        # 색상 폴더 내의 파일들
        for color_dir in example_product_path.iterdir():
            if not color_dir.is_dir():
                continue

            for file in sorted(color_dir.glob('*.jpg')):
                img = Image.open(file)
                size = img.size

                if size not in size_to_files:
                    size_to_files[size] = []

                size_to_files[size].append(file.name)
    else:
        # 색상 폴더 없이 직접 파일
        for file in sorted(example_product_path.glob('*.jpg')):
            img = Image.open(file)
            size = img.size

            if size not in size_to_files:
                size_to_files[size] = []

            size_to_files[size].append(file.name)

    return size_to_files


def get_color_abbreviation(color_name: str) -> str:
    """색상명을 약자로 변환"""
    # 예: AGED BLUE -> AB, CHOCO BROWN -> CHB
    parts = color_name.upper().split()
    abbr = ''.join([p[0] for p in parts if p])
    return abbr


def generate_new_filename(example_filename: str, new_color_abbr: str) -> str:
    """
    예시 파일명에서 색상 부분을 새로운 색상 약자로 변경
    예: CHOCO-BROWN-1.jpg -> AB-1.jpg
    """
    # 썸네일은 그대로 유지
    if '썸네일' in example_filename:
        return example_filename

    # 파일명에서 숫자 부분만 추출
    parts = example_filename.rsplit('.', 1)
    base = parts[0]
    ext = parts[1] if len(parts) > 1 else 'jpg'

    # 숫자 추출 (뒤쪽에서부터)
    match = re.search(r'(\d+)$', base)
    if match:
        number = match.group(1)
        return f"{new_color_abbr}-{number}.{ext}"

    # 숫자가 없으면 그대로 반환
    return example_filename


def process_nuki_image(nuki_path: Path, target_size: Tuple[int, int], example_position=None) -> Image.Image:
    """누끼 이미지를 처리하여 지정된 크기로 리사이징"""
    original = Image.open(nuki_path)
    transparent = remove_white_background(original)
    product = crop_product(transparent)
    resized = resize_to_spec(product, target_size[0], target_size[1], example_position)
    return resized


def main(nuki_folder: str, example_folder: str, output_folder: str):
    """메인 처리 함수"""
    print("=" * 80)
    print("상품 이미지 자동 리사이징 시작")
    print("=" * 80)

    nuki_path = Path(nuki_folder)
    example_path = Path(example_folder)
    output_path = Path(output_folder)

    # 누끼 이미지 폴더에서 상품별 처리
    for product_dir in sorted(nuki_path.iterdir()):
        if not product_dir.is_dir():
            continue

        product_name = product_dir.name
        print(f"\n상품: {product_name}")

        # 색상별 이미지 처리
        for color_dir in sorted(product_dir.iterdir()):
            if not color_dir.is_dir():
                continue

            new_color_name = color_dir.name
            new_color_abbr = get_color_abbreviation(new_color_name)
            print(f"  색상: {new_color_name} ({new_color_abbr})")

            # 누끼 이미지 파일들
            nuki_images = sorted(color_dir.glob('*.jpg'))

            # 각 채널사별 처리
            for channel_name, channel_info in CHANNEL_SPECS.items():
                example_product_path = example_path / channel_info['example_path'] / product_name

                if not example_product_path.exists():
                    print(f"    {channel_name}: 예시 폴더 없음")
                    continue

                # 예시 파일들 분류
                size_to_files = get_example_files(example_product_path, channel_info['has_color_folder'])

                if not size_to_files:
                    print(f"    {channel_name}: 예시 파일 없음")
                    continue

                print(f"    {channel_name}:")

                # 각 규격별 처리
                for target_size in channel_info['sizes']:
                    if target_size not in size_to_files:
                        print(f"      {target_size[0]}x{target_size[1]}: 예시 파일 없음")
                        continue

                    print(f"      {target_size[0]}x{target_size[1]}")

                    example_filenames = size_to_files[target_size]
                    output_product_path = (
                        output_path /
                        channel_info['output_path'] /
                        product_name /
                        new_color_name
                    )
                    output_product_path.mkdir(parents=True, exist_ok=True)

                    # 예시 이미지에서 상품 위치 분석
                    example_position = None
                    if channel_info['has_color_folder']:
                        first_color_dir = next(example_product_path.iterdir())
                        first_example = next((f for f in first_color_dir.glob('*.jpg') if target_size == Image.open(f).size), None)
                    else:
                        first_example = next((f for f in example_product_path.glob('*.jpg') if target_size == Image.open(f).size), None)

                    if first_example:
                        example_img = Image.open(first_example)
                        example_position = analyze_product_position(example_img)

                    # 누끼 이미지들을 리사이징하여 저장
                    for idx, (nuki_img_path, example_filename) in enumerate(
                        zip(nuki_images, example_filenames)
                    ):
                        # 파일명 생성
                        if '썸네일' in example_filename:
                            new_filename = example_filename
                        else:
                            new_filename = generate_new_filename(example_filename, new_color_abbr)

                        # 리사이징
                        resized = process_nuki_image(nuki_img_path, target_size, example_position)

                        # 저장
                        output_file = output_product_path / new_filename
                        resized.save(output_file, 'JPEG', quality=95)
                        print(f"        저장: {output_file.relative_to(output_path)}")

    print("\n" + "=" * 80)
    print("리사이징 완료!")
    print("=" * 80)


if __name__ == '__main__':
    nuki_folder = '누끼 이미지'
    example_folder = '예시 결과물'
    output_folder = '★엠디 작업용'

    if not Path(nuki_folder).exists():
        print(f"오류: {nuki_folder} 폴더를 찾을 수 없습니다")
        exit(1)

    if not Path(example_folder).exists():
        print(f"오류: {example_folder} 폴더를 찾을 수 없습니다")
        exit(1)

    main(nuki_folder, example_folder, output_folder)
