import fitz
from deep_translator import GoogleTranslator
import unicodedata
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Configuration
INPUT = "input.pdf"
OUTPUT = "output.pdf"
FONT_PATH = get_resource_path("NotoSans-Regular.ttf")

# ========================
# 🚀 ADD CACHE (TỐI ƯU)
# ========================
translation_cache = {}


def wrap_text(text, font_size, max_width):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word if current_line else word

        width = fitz.get_text_length(
            test_line,
            fontname="helv",
            fontsize=font_size
        )

        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def fit_text_to_box(text, bbox, font_size):
    max_width = bbox[2] - bbox[0]
    max_height = bbox[3] - bbox[1]

    min_font = 5
    line_spacing = 1.2

    while font_size >= min_font:
        lines = wrap_text(text, font_size, max_width)

        total_height = len(lines) * font_size * line_spacing

        if total_height <= max_height:
            return lines, font_size

        font_size -= 0.5

    return lines, min_font


# ========================
# 🚀 SAFE TRANSLATE
# ========================

def normalize_key(text):
    return " ".join(text.strip().split())


def translate_text(text):
    if not text or not text.strip():
        return ""

    key = normalize_key(text)

    # ✅ USE NORMALIZED KEY
    if key in translation_cache:
        return translation_cache[key]

    # 👉 THREAD-SAFE TRANSLATOR
    try:
        local_translator = GoogleTranslator(source="auto", target="vi")
        result = local_translator.translate(text)

        translation_cache[key] = result if result else text
        return translation_cache[key]
    except:
        pass

    # 👉 FALLBACK OFFLINE
    try:
        import argostranslate.translate
        result = argostranslate.translate.translate(text, "en", "vi")

        translation_cache[key] = result if result else text
        return translation_cache[key]
    except:
        translation_cache[key] = text
        return text


# ========================
# 🚀 PARALLEL TRANSLATION
# ========================
def parallel_translate(texts, max_workers=4):
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(translate_text, text): text
            for text in texts
        }

        for future in as_completed(future_map):
            original = future_map[future]
            try:
                results[original] = future.result()
            except:
                results[original] = original

    return results


def translate_pdf(input_path, output_path, progress_callback=None, cancel_callback=None):
    doc = fitz.open(input_path)
    new_doc = fitz.open()

    # 👉 LOAD FONT AN TOÀN
    has_custom_font = False
    if os.path.exists(FONT_PATH):
        has_custom_font = True
    else:
        print("⚠️ Font not found, fallback to Helvetica")

    total_pages = len(doc)


    for i_page, page in enumerate(doc):
        if cancel_callback and cancel_callback():
            doc.close()
            new_doc.close()
            return False

        new_page = new_doc.new_page(
            width=page.rect.width,
            height=page.rect.height
        )

        # 👉 COPY FULL PAGE (GIỮ 100% LAYOUT + IMAGE)
        new_page.show_pdf_page(new_page.rect, doc, page.number)

        data = page.get_text("dict")

        # ========================
        # 🚀 COLLECT + DEDUP TEXT
        # ========================
        all_texts = []

        for block in data["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    txt = span["text"]
                    if txt.strip():
                        all_texts.append(txt)

        unique_texts = list(set(all_texts))

        # 👉 PARALLEL TRANSLATE
        translated_map = parallel_translate(unique_texts)

        # ========================
        # 👉 STEP 1: ADD REDACTION
        # ========================
        for block in data["blocks"]:
            if block["type"] != 0:
                continue

            for line in block["lines"]:
                for span in line["spans"]:

                    original_text = span["text"]
                    if not original_text.strip():
                        continue

                    rect = fitz.Rect(span["bbox"])
                    new_page.add_redact_annot(rect, fill=(1, 1, 1))

        new_page.apply_redactions()

        # ========================
        # 👉 STEP 2: DRAW TEXT
        # ========================
        for block in data["blocks"]:
            if block["type"] != 0:
                continue

            for line in block["lines"]:
                for span in line["spans"]:

                    original_text = span["text"]
                    if not original_text.strip():
                        continue

                    translated = translated_map.get(original_text, original_text)
                    clean_text = unicodedata.normalize("NFC", str(translated))

                    bbox = span["bbox"]
                    font_size = span["size"]

                    # 👉 CHỌN FONT ĐỂ VẼ
                    draw_font = "helv"
                    if has_custom_font:
                        draw_font = "vi"
                        if "vi" not in new_page.get_fonts():
                            new_page.insert_font("vi", FONT_PATH)

                    # 👉 AUTO FIT
                    while font_size > 5:
                        text_width = fitz.get_text_length(
                            clean_text,
                            fontname="helv",
                            fontsize=font_size
                        )

                        if text_width <= (bbox[2] - bbox[0]):
                            break

                        font_size -= 0.5

                    # 👉 FIT TEXT BOX
                    wrapped_lines, final_font_size = fit_text_to_box(
                        clean_text,
                        bbox,
                        span["size"]
                    )

                    x = bbox[0]
                    y = bbox[3]
                    line_height = final_font_size * 1.2

                    for i, text_line in enumerate(wrapped_lines):
                        new_page.insert_text(
                            (x, y + i * line_height),
                            text_line,
                            fontsize=final_font_size,
                            fontname=draw_font,
                            color=(0, 0, 0)
                        )
                        
        if progress_callback:
            progress_callback(i_page + 1, total_pages)

    new_doc.save(output_path)
    doc.close()
    new_doc.close()
    return True

if __name__ == "__main__":
    from ui import start_app
    start_app()