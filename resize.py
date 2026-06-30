#!/usr/bin/env python3
"""
원본 이미지를 예시 이미지의 규격에 맞춰서 리사이징
"""

from PIL import Image
from pathlib import Path
from collections import defaultdict


def get_example_specs():
    """예시 폴더에서 이미지 규격 파악"""
    example_path = Path('example')
    specs = defaultdict  # (width, height) -> count

    if not example_path.exists():
        print("example 폴더가 없습니다")
        return {}

    for img_file in example_path.glob('*.jpg'):
        img = Image.open(img_file)
        size = img.size
        if size not in specs:
            specs[size] = 0
        specs[size] += 1

    return specs


def resize_images():
    """원본 이미지를 예시 규격에 맞춰 리사이징"""
    example_path = Path('example')
    original_path = Path('original')
    work_path = Path('work')

    # 폴더 확인
    if not example_path.exists():
        print("❌ example 폴더가 없습니다")
        return

    if not original_path.exists():
        print("❌ original 폴더가 없습니다")
        return

    work_path.mkdir(exist_ok=True)

    # 예시 규격 파악
    example_specs = {}
    for img_file in sorted(example_path.glob('*.jpg')):
        img = Image.open(img_file)
        size = img.size
        if size not in example_specs:
            example_specs[size] = img_file.name

    if not example_specs:
        print("❌ example 폴더에 jpg 파일이 없습니다")
        return

    print(f"\n예시 이미지 규격:")
    for size, filename in example_specs.items():
        print(f"  {size[0]}x{size[1]} ({filename})")

    # 원본 이미지 리사이징
    original_images = sorted(original_path.glob('*.jpg'))
    if not original_images:
        print("❌ original 폴더에 jpg 파일이 없습니다")
        return

    print(f"\n원본 이미지 리사이징 중...")
    for original_file in original_images:
        original_img = Image.open(original_file)

        # 첫 번째 규격으로 리사이징
        target_size = list(example_specs.keys())[0]

        # 리사이징
        resized = original_img.resize(target_size, Image.Resampling.LANCZOS)

        # 저장
        output_file = work_path / original_file.name
        resized.save(output_file, 'JPEG', quality=95)
        print(f"  저장: {original_file.name} → {target_size[0]}x{target_size[1]}")

    print(f"\n✅ 리사이징 완료! ({work_path}에 저장됨)")


if __name__ == '__main__':
    resize_images()
