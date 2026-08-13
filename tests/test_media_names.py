from pathlib import Path


def test_image_media_names_use_cover_and_inner_page_labels():
    from xhs_dl.core.media_names import media_filename

    assert media_filename(0, "标题/测试", ".webp", is_video=False) == "封面-标题_测试.webp"
    assert media_filename(1, "标题/测试", ".png", is_video=False) == "内页1-标题_测试.png"
    assert media_filename(2, "标题/测试", ".jpg", is_video=False) == "内页2-标题_测试.jpg"


def test_video_media_name_uses_title():
    from xhs_dl.core.media_names import media_filename

    assert media_filename(0, "巡演：第一场", ".mp4", is_video=True) == "视频-巡演：第一场.mp4"
    assert media_filename(1, "巡演：第一场", ".mp4", is_video=True) == "视频2-巡演：第一场.mp4"


def test_image_can_be_converted_to_jpg_or_png(tmp_path):
    from PIL import Image
    from xhs_dl.core.media_names import convert_image_file

    source = tmp_path / "source.webp"
    Image.new("RGBA", (3, 2), (20, 40, 60, 128)).save(source, "WEBP")

    jpg = convert_image_file(source, "jpg")
    assert jpg.suffix == ".jpg"
    assert Image.open(jpg).format == "JPEG"

    png = convert_image_file(jpg, "png")
    assert png.suffix == ".png"
    assert Image.open(png).format == "PNG"


def test_mixed_media_keeps_cover_numbering_independent_from_video(tmp_path):
    from PIL import Image
    from xhs_dl.core.v2_downloader import LocalCliEngine

    video = tmp_path / "00-video.mp4"
    cover = tmp_path / "10-cover.webp"
    inner = tmp_path / "20-inner.webp"
    video.write_bytes(b"video")
    Image.new("RGB", (2, 2), "red").save(cover, "WEBP")
    Image.new("RGB", (2, 2), "blue").save(inner, "WEBP")

    renamed = LocalCliEngine._rename_media_files(
        [video, inner, cover], "混合媒体", "jpg"
    )

    assert {path.name for path in renamed} == {
        "封面-混合媒体.jpg",
        "内页1-混合媒体.jpg",
        "视频-混合媒体.mp4",
    }


def test_media_sort_key_uses_natural_numeric_order():
    from xhs_dl.core.media_names import media_sort_key

    paths = [Path("图片_10.png"), Path("图片_2.png"), Path("图片_1.png")]

    assert [path.name for path in sorted(paths, key=media_sort_key)] == [
        "图片_1.png", "图片_2.png", "图片_10.png"
    ]
