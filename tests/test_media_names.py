def test_image_media_names_use_cover_and_inner_page_labels():
    from xhs_dl.core.media_names import media_filename

    assert media_filename(0, "标题/测试", ".webp", is_video=False) == "封面-标题_测试.webp"
    assert media_filename(1, "标题/测试", ".png", is_video=False) == "内页1-标题_测试.png"
    assert media_filename(2, "标题/测试", ".jpg", is_video=False) == "内页2-标题_测试.jpg"


def test_video_media_name_uses_title():
    from xhs_dl.core.media_names import media_filename

    assert media_filename(0, "巡演：第一场", ".mp4", is_video=True) == "视频-巡演：第一场.mp4"


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
