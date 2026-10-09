# -*- coding: utf-8 -*-
# THESIS: CIC文書を「安全な検査台」として扱い、汎用PDF編集画面の複雑さを拒む。
# OWN-WORLD: 深い紺、紙の白、検証済みを示す青緑。帳票の罫線と黒い削除帯を部品言語にする。
# STORY: PDFを選ぶ、検出結果を確認する、復元不能なコピーを保存する、という一本道。
# FIRST VIEWPORT: 左に3段階の検査工程、右に大きな選択面と安全性の要約、下端に主操作。
# FORM: grounded direction 5, secure document inspection station; seed 1b41bc2e.
# FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

from __future__ import annotations

import io
import ctypes
import hashlib
import math
import ntpath
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from queue import Empty, Queue
from typing import Callable, Iterable

# PyMuPDF reads these at import time: they can open files or import external code.
# Always use its normal, bundled runtime and never inherit file logging settings.
for _environment_option in ("PYMUPDF_LOG", "PYMUPDF_MESSAGE", "MUPDF_CPPYY"):
    os.environ.pop(_environment_option, None)

import pymupdf
pymupdf.TOOLS.mupdf_display_errors(False)
pymupdf.TOOLS.mupdf_display_warnings(False)
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_NAME = "CIC Personal Data Remover"
APP_TITLE = "CIC 個人情報削除ツール"
APP_VERSION = "1.1.1"
NAME_ONLY_NOTICE = "申込情報・利用記録は氏名のみ削除。生年月日・電話番号等は残ります。"

COLOR_BG = "#0B1424"
COLOR_PANEL = "#111D30"
COLOR_PANEL_2 = "#17263A"
COLOR_PAPER = "#F4F1E8"
COLOR_INK = "#102033"
COLOR_WHITE = "#F7FAFC"
COLOR_MUTED = "#AFC0D3"
COLOR_ACCENT = "#35D3BE"
COLOR_ACCENT_DARK = "#0B7469"
COLOR_WARNING = "#F3B85B"
COLOR_ERROR = "#FF7A7A"
COLOR_BLACK = "#000000"

RECEIPT_NUMBER = re.compile(r"\b\d{2}-[A-Z0-9]{2}-\d{6}\b", re.IGNORECASE)
LAYOUT_NAMES = {
    "summary": "照会入力情報",
    "credit": "クレジット情報",
    "application": "申込情報（氏名のみ削除）",
    "usage": "利用記録（氏名のみ削除）",
    "reference": "参考情報",
    "cover": "CIC表紙",
    "unrecognized": "未認識（全面黒塗り）",
}


class UnsupportedDocumentError(RuntimeError):
    """Raised when the requested conversion cannot be completed safely."""


@dataclass(frozen=True)
class MaskRegion:
    rect: pymupdf.Rect
    category: str


@dataclass
class PagePlan:
    page_index: int
    layout: str
    regions: list[MaskRegion] = field(default_factory=list)
    full_mask: bool = False


@dataclass
class Analysis:
    input_path: Path
    page_count: int
    plans: list[PagePlan]
    input_sha256: str

    @property
    def masked_region_count(self) -> int:
        return sum(len(plan.regions) for plan in self.plans)

    @property
    def affected_page_count(self) -> int:
        return sum(bool(plan.regions) for plan in self.plans)

    @property
    def unrecognized_page_count(self) -> int:
        return sum(plan.layout == "unrecognized" for plan in self.plans)

    @property
    def fully_masked_page_count(self) -> int:
        return sum(plan.full_mask for plan in self.plans)


@dataclass
class ProcessResult:
    output_path: Path
    page_count: int
    masked_region_count: int
    output_size: int
    unrecognized_page_count: int
    fully_masked_page_count: int


def _rect(value: tuple[float, float, float, float] | pymupdf.Rect) -> pymupdf.Rect:
    return value if isinstance(value, pymupdf.Rect) else pymupdf.Rect(value)


def _cell(table, row: int, column: int, category: str) -> MaskRegion:
    try:
        value = table.rows[row].cells[column]
    except (IndexError, AttributeError) as exc:
        raise UnsupportedDocumentError("CIC帳票の表構造が想定と異なります。") from exc
    if value is None:
        raise UnsupportedDocumentError("個人情報欄の境界を安全に特定できませんでした。")
    box = _rect(value)
    _validate_box(box, pymupdf.Rect(table.bbox))
    return MaskRegion(box, category)


def _validate_box(box: pymupdf.Rect, container: pymupdf.Rect) -> None:
    if (not all(math.isfinite(value) for value in box)
            or box.is_empty or box.is_infinite
            or box.x0 < container.x0 - 2 or box.y0 < container.y0 - 2
            or box.x1 > container.x1 + 2 or box.y1 > container.y1 + 2):
        raise UnsupportedDocumentError("帳票の領域が想定と異なります。ページ全体を黒塗りします。")


def _validate_table(table, page_rect: pymupdf.Rect) -> None:
    box = pymupdf.Rect(table.bbox)
    _validate_box(box, page_rect)
    if not table.rows:
        raise UnsupportedDocumentError("表の行を確認できません。")
    for row in table.rows:
        for value in row.cells:
            if value is not None:
                _validate_box(pymupdf.Rect(value), box)


def _unknown_plan(page: pymupdf.Page, page_index: int) -> PagePlan:
    return PagePlan(page_index, "unrecognized", [MaskRegion(pymupdf.Rect(page.rect), "ページ全体")], True)


def _same_size(page: pymupdf.Page) -> bool:
    width, height = page.rect.width, page.rect.height
    return abs(width - 842.0) <= 18.0 and abs(height - 595.0) <= 18.0


def _header_identifiers(page: pymupdf.Page) -> list[MaskRegion]:
    regions: list[MaskRegion] = []
    for word in page.get_text("words"):
        text = str(word[4]).strip()
        if RECEIPT_NUMBER.search(text):
            # Text coordinates in CIC's rotated pages use the unrotated PDF space,
            # while table geometry and rendered pixels use the visible page space.
            box = pymupdf.Rect(word[:4]) * page.rotation_matrix
            box.x0 -= 1.5
            box.y0 -= 1.0
            box.x1 += 1.5
            box.y1 += 1.0
            regions.append(MaskRegion(box, "受付番号"))
    return regions


def _summary_extra_masks() -> list[MaskRegion]:
    """Header areas of the validated landscape summary, independent of page order."""
    return [
        MaskRegion(pymupdf.Rect(0.0, 82.0, 185.0, 145.0), "宛名"),
        MaskRegion(pymupdf.Rect(600.0, 8.0, 842.0, 78.0), "開示情報"),
    ]


def _classify_page(page: pymupdf.Page, page_index: int) -> PagePlan:
    try:
        return _classify_known_page(page, page_index)
    except Exception:
        # Extraction/geometry failures must never fall back to a partly exposed page.
        return _unknown_plan(page, page_index)


def _classify_known_page(page: pymupdf.Page, page_index: int) -> PagePlan:
    if not _same_size(page):
        return _unknown_plan(page, page_index)

    words = page.get_text("words")
    tables = page.find_tables().tables
    regions = _header_identifiers(page)

    if len(tables) == 0:
        visible_text = " ".join(str(word[4]) for word in words)
        cover_anchors = (
            "Copyright" in visible_text
            and "CREDIT INFORMATION CENTER CORP." in visible_text
            and "All rights reserved" in visible_text
        )
        if len(words) <= 20 and cover_anchors:
            # A text-only copyright anchor does not prove the absence of other data.
            return PagePlan(page_index, "cover", [MaskRegion(pymupdf.Rect(page.rect), "ページ全体（表紙）")], True)
        return _unknown_plan(page, page_index)

    for table in tables:
        _validate_table(table, page.rect)

    first = tables[0]
    rows = len(first.rows)
    x0, y0, x1, y1 = first.bbox
    width = x1 - x0

    # First-page query summary: every right-column value is personal data.
    max_columns = max((len(row.cells) for row in first.rows), default=0)
    if (len(tables) == 1 and rows == 10 and max_columns == 2
            and 450 <= x0 <= 550 and 300 <= y0 <= 400
            and 230 <= width <= 330 and 120 <= y1 - y0 <= 210):
        regions.extend(_summary_extra_masks())
        regions.extend(_cell(first, row, 1, "照会入力情報") for row in range(rows))
        return PagePlan(page_index, "summary", regions)

    # Credit / spouse information pages have the 13-row attribute table followed by
    # contract and payment tables. Keep labels, delete only value cells.
    if (len(tables) >= 5 and rows == 13 and max_columns == 4
            and 0 <= x0 <= 50 and 50 <= y0 <= 110
            and 500 <= width <= 570 and 150 <= y1 - y0 <= 220):
        cells = [
            (0, 1, "氏名"),
            (1, 1, "氏名"),
            (2, 1, "生年月日"),
            (2, 3, "性別"),
            (3, 1, "電話番号"),
            (4, 1, "住所"),
            (5, 1, "住所"),
            (6, 1, "勤務先"),
            (7, 1, "勤務先電話"),
            (8, 2, "本人確認番号"),
            (9, 2, "本人確認情報"),
            (10, 2, "本人確認情報"),
            (11, 2, "本人確認情報"),
            (12, 1, "配偶者氏名"),
        ]
        regions.extend(_cell(first, r, c, name) for r, c, name in cells)
        return PagePlan(page_index, "credit", regions)

    # Reference / declaration page: left half is identity data; the free-text comment
    # can contain identity-document details and is therefore removed in full.
    if (len(tables) == 1 and rows == 10 and 750 <= width <= 825
            and 0 <= x0 <= 50 and 50 <= y0 <= 110
            and 110 <= y1 - y0 <= 180 and max_columns == 4):
        for row, category in [
            (1, "氏名"),
            (2, "生年月日"),
            (3, "郵便番号"),
            (4, "電話番号"),
            (5, "性別"),
            (6, "住所"),
            (7, "住所"),
            (8, "勤務先"),
            (9, "勤務先電話"),
        ]:
            regions.append(_cell(first, row, 1, category))
        regions.append(_cell(first, 6, 2, "本人申告コメント"))
        return PagePlan(page_index, "reference", regions)

    # Application information pages repeat a wide ten-row table for each inquiry.
    if all(
        len(table.rows) == 10
        and 750 <= (table.bbox[2] - table.bbox[0]) <= 825
        and 85 <= (table.bbox[3] - table.bbox[1]) <= 150
        and 0 <= table.bbox[0] <= 50
        and max((len(row.cells) for row in table.rows), default=0) == 6
        for table in tables
    ):
        name_regions: list[MaskRegion] = []
        for table in tables:
            # Both displayed name rows belong to this merged value cell. Preserve
            # all remaining values and headers under this explicit name-only policy.
            if table.rows[2].cells[1] is not None:
                raise UnsupportedDocumentError("氏名欄の結合構造が想定と異なります。")
            name_regions.append(_cell(table, 1, 1, "氏名"))
        return PagePlan(page_index, "application", name_regions)

    # Usage records use the same requested name-only policy as application pages.
    if (len(tables) == 1 and rows == 5 and max_columns == 2
            and 300 <= width <= 450 and 0 <= x0 <= 50
            and 50 <= y0 <= 120 and 55 <= y1 - y0 <= 100):
        return PagePlan(page_index, "usage", [_cell(first, 1, 1, "氏名")])

    return _unknown_plan(page, page_index)


def _cloud_roots() -> list[Path]:
    roots = [Path(value) for name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial",
                                      "Dropbox", "GoogleDrive", "iCloudDrive")
             if (value := os.environ.get(name))]
    if os.name == "nt":
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\Explorer\SyncRootManager") as manager:
                    for index in range(winreg.QueryInfoKey(manager)[0]):
                        try:
                            with winreg.OpenKey(manager, winreg.EnumKey(manager, index) + r"\UserSyncRoots") as users:
                                for item in range(winreg.QueryInfoKey(users)[1]):
                                    _, value, _ = winreg.EnumValue(users, item)
                                    if isinstance(value, str):
                                        roots.append(Path(value))
                        except OSError:
                            continue
            except OSError:
                continue
    return roots


def _fixed_drive(root: str) -> bool:
    function = ctypes.windll.kernel32.GetDriveTypeW
    function.argtypes = [ctypes.c_wchar_p]
    function.restype = ctypes.c_uint
    return function(root) == 3  # DRIVE_FIXED only; never probe a mapped remote drive.


def _local_path(value: str | os.PathLike[str]) -> Path:
    raw = os.fspath(value)
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise ValueError("ローカル固定ディスクのファイルを指定してください。")
    normalized = raw.replace("/", "\\")
    if normalized.startswith("\\\\") or normalized.startswith("\\??\\"):
        raise ValueError("ネットワーク共有・デバイスパスには対応していません。")
    for part in normalized.split("\\"):
        if (part not in ("", ".", "..")
                and (PureWindowsPath(part).is_reserved() or part.endswith((".", " ")))):
            raise ValueError("予約されたデバイス名・末尾の空白やピリオドは使用できません。")
    if os.name == "nt":
        drive, tail = ntpath.splitdrive(normalized)
        if (drive and not tail.startswith("\\")) or ":" in tail:
            raise ValueError("通常のローカルファイルパスを指定してください。")
        absolute = Path(ntpath.abspath(normalized))
        if str(absolute).replace("/", "\\").startswith(("\\\\", "\\??\\")):
            raise ValueError("ネットワーク共有・デバイスパスには対応していません。")
        if not absolute.drive or not _fixed_drive(absolute.anchor):
            raise ValueError("ネットワーク・外付けドライブは使用できません。ローカル固定ディスクを選んでください。")
    else:
        if ntpath.splitdrive(normalized)[0]:
            raise ValueError("この端末のローカルファイルを指定してください。")
        absolute = Path(os.path.abspath(raw))

    cloud_names = {"onedrive", "dropbox", "google drive", "googledrive", "my drive", "iclouddrive"}
    if any(part.casefold() in cloud_names or part.casefold().startswith("onedrive - ") for part in absolute.parts):
        raise ValueError("同期フォルダは使用できません。同期しないローカルフォルダを選んでください。")
    for root in _cloud_roots():
        # Lexical comparison intentionally precedes all filesystem access.
        root = Path(os.path.abspath(root))
        if absolute == root or root in absolute.parents:
            raise ValueError("同期フォルダは使用できません。同期しないローカルフォルダを選んでください。")

    # Reject junctions, symbolic links, and cloud placeholders before following them.
    # Resolving a local link first could itself access a UNC/network target.
    for component in reversed((absolute, *absolute.parents)):
        try:
            info = os.lstat(component)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("リンク・同期プレースホルダーを含む保存場所には対応していません。")
    return absolute


def _read_input(path: Path) -> bytes:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("PDFファイルが見つかりません。")
    if path.suffix.lower() != ".pdf":
        raise UnsupportedDocumentError("PDFファイルを選択してください。")
    return path.read_bytes()


def analyze_document(input_path: str | os.PathLike[str]) -> Analysis:
    path = _local_path(input_path)
    snapshot = _read_input(path)
    fingerprint = hashlib.sha256(snapshot).hexdigest()

    try:
        document = pymupdf.open(stream=snapshot, filetype="pdf")
    except Exception as exc:
        raise UnsupportedDocumentError("PDFを開けません。破損または未対応の暗号化形式です。") from exc

    try:
        if document.needs_pass and not document.authenticate(""):
            raise UnsupportedDocumentError("パスワードが必要なPDFには対応していません。")
        if document.page_count == 0:
            raise UnsupportedDocumentError("ページのないPDFです。")
        plans = [_classify_page(page, index) for index, page in enumerate(document)]
        return Analysis(path, document.page_count, plans, fingerprint)
    finally:
        document.close()


def _safe_rect(rect: pymupdf.Rect, page_rect: pymupdf.Rect) -> pymupdf.Rect:
    # Erase outward, including antialiasing/glyphs touching the cell border.
    safe = pymupdf.Rect(rect)
    if not all(math.isfinite(value) for value in safe) or safe.is_empty:
        raise UnsupportedDocumentError("削除領域を確認できません。PDFをもう一度選択してください。")
    safe.x0 -= 1.25
    safe.y0 -= 1.25
    safe.x1 += 1.25
    safe.y1 += 1.25
    return safe & page_rect


def _render_masked_page(page: pymupdf.Page, regions: Iterable[MaskRegion], dpi: int = 180,
                        full_mask: bool = False) -> bytes:
    if full_mask:
        # Stretch one black pixel to the page bounds. Do not render/read its content.
        with Image.new("RGB", (1, 1), (0, 0, 0)) as image:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()
    scale = dpi / 72.0
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False, annots=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    draw = ImageDraw.Draw(image)
    for region in regions:
        rect = _safe_rect(region.rect, page.rect)
        if rect.is_empty:
            raise UnsupportedDocumentError("削除領域がページ外です。PDFをもう一度選択してください。")
        draw.rectangle(
            (
                math.floor(rect.x0 * scale),
                math.floor(rect.y0 * scale),
                math.ceil(rect.x1 * scale),
                math.ceil(rect.y1 * scale),
            ),
            fill=(0, 0, 0),
        )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    image.close()
    return buffer.getvalue()


def process_document(
    analysis: Analysis,
    output_path: str | os.PathLike[str],
    progress: Callable[[int, int, str], None] | None = None,
) -> ProcessResult:
    output = _local_path(output_path)
    input_path = _local_path(analysis.input_path)
    if output == input_path or (output.exists() and os.path.samefile(output, input_path)):
        raise ValueError("元のPDFは上書きできません。別の保存先を選択してください。")
    if output.suffix.lower() != ".pdf":
        raise ValueError("保存先はPDFファイル名を指定してください。")
    snapshot = _read_input(input_path)
    if hashlib.sha256(snapshot).hexdigest() != analysis.input_sha256:
        raise UnsupportedDocumentError("選択後に元PDFが変更されました。PDFを選び直してください。")
    if len(analysis.plans) != analysis.page_count or any(
        plan.page_index != index for index, plan in enumerate(analysis.plans)
    ):
        raise UnsupportedDocumentError("検出結果が変更されました。PDFを選び直してください。")

    # Parse and render the exact immutable bytes whose identity was just checked.
    # No input snapshot or unfinished PDF is written to disk.
    with pymupdf.open(stream=snapshot, filetype="pdf") as source, pymupdf.open() as sanitized:
        if source.needs_pass and not source.authenticate(""):
            raise UnsupportedDocumentError("PDFの読み込み権限を確認できません。")
        total = analysis.page_count
        for index, plan in enumerate(analysis.plans):
            if progress:
                progress(index, total, f"{index + 1} / {total} ページの削除領域を画像化しています")
            source_page = source[index]
            png = _render_masked_page(source_page, plan.regions, full_mask=plan.full_mask)
            target = sanitized.new_page(width=source_page.rect.width, height=source_page.rect.height)
            target.insert_image(target.rect, stream=png, keep_proportion=False)

        sanitized.set_metadata({})
        completed_pdf = sanitized.tobytes(garbage=4, deflate=True, clean=True)

    if progress:
        progress(total, total, "文字層・添付・メタデータ・リンクなどを検証しています")
    _verify_pdf(completed_pdf, analysis.page_count)
    # Only a verified result reaches disk. The exclusively created filename never
    # derives from the input/output stem and cleanup only owns this call's file.
    output.parent.mkdir(parents=True, exist_ok=True)
    output = _local_path(output)
    descriptor: int | None = None
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".cic-masker-", suffix=".tmp", dir=output.parent)
        temporary = Path(name)
        handle = os.fdopen(descriptor, "wb")
        descriptor = None  # The context manager now owns the descriptor.
        with handle:
            handle.write(completed_pdf)
            handle.flush()
            os.fsync(handle.fileno())
        output = _local_path(output)
        if output == input_path or (output.exists() and os.path.samefile(output, input_path)):
            raise ValueError("元のPDFと同じファイルには保存できません。")
        os.replace(temporary, output)
        temporary = None
    except BaseException as failure:
        cleanup_errors = []
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if cleanup_errors:
            raise RuntimeError("保存に失敗し、一時ファイルの後始末も完了しませんでした。"
                               "選択した保存先の .cic-masker- で始まる .tmp ファイルを確認してください。") from failure
        raise
    if progress:
        progress(total, total, "構造の検証が完了しました。共有前に出力を目視確認してください")
    return ProcessResult(output, analysis.page_count, analysis.masked_region_count,
                         len(completed_pdf), analysis.unrecognized_page_count,
                         analysis.fully_masked_page_count)


def _verify_pdf(data: bytes, page_count: int) -> None:
    with pymupdf.open(stream=data, filetype="pdf") as verify:
        if verify.page_count != page_count:
            raise RuntimeError("出力PDFのページ数が一致しません。")
        for page in verify:
            if (page.get_text() or "").strip():
                raise RuntimeError("出力PDFに文字データが残っています。")
            if page.get_links() or page.first_annot is not None or list(page.widgets() or ()):
                raise RuntimeError("出力PDFにリンク・注釈・フォームが残っています。")
        if verify.embfile_count() or verify.get_toc() or verify.get_xml_metadata():
            raise RuntimeError("出力PDFに添付・目次・XMLメタデータが残っています。")
        metadata_fields = ("title", "author", "subject", "keywords", "creator", "producer",
                           "creationDate", "modDate", "trapped")
        if any(verify.metadata.get(key) for key in metadata_fields):
            raise RuntimeError("出力PDFにメタデータが残っています。")
        for index in range(1, verify.xref_length()):
            if re.search(r"/(?:JavaScript|JS|OpenAction|AA|Launch)\b", verify.xref_object(index)):
                raise RuntimeError("出力PDFに実行アクションが残っています。")


class CICMaskerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE}  {APP_VERSION}")
        self.geometry("1000x840")
        self.minsize(920, 800)
        self.configure(bg=COLOR_BG)
        self.option_add("*Font", ("Noto Sans JP", 10))
        self.protocol("WM_DELETE_WINDOW", self._request_close)

        try:
            self.tk.call("tk", "scaling", 1.2)
        except tk.TclError:
            pass

        self.analysis: Analysis | None = None
        self.last_output: Path | None = None
        self.events: Queue[tuple[str, object]] = Queue()
        self.busy = False
        self.worker: threading.Thread | None = None

        self._configure_styles()
        self._build_ui()
        self.after(80, self._poll_events)

        if len(sys.argv) > 1 and Path(sys.argv[1]).suffix.lower() == ".pdf":
            self.after(250, lambda: self._analyze(Path(sys.argv[1])))

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Primary.TButton",
            background=COLOR_ACCENT,
            foreground=COLOR_INK,
            borderwidth=0,
            padding=(20, 13),
            font=("Noto Sans JP", 11, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#69E5D5"), ("disabled", "#33485A")],
            foreground=[("disabled", "#8192A4")],
        )
        style.configure(
            "Secondary.TButton",
            background=COLOR_PANEL_2,
            foreground=COLOR_WHITE,
            bordercolor="#36506A",
            borderwidth=1,
            padding=(16, 11),
            font=("Noto Sans JP", 10, "bold"),
        )
        style.map("Secondary.TButton", background=[("active", "#223A53")])
        style.configure(
            "Secure.Horizontal.TProgressbar",
            troughcolor="#24364A",
            background=COLOR_ACCENT,
            borderwidth=0,
            thickness=8,
        )

    def _build_ui(self) -> None:
        top = tk.Frame(self, bg=COLOR_BG, height=76)
        top.pack(fill="x", padx=38, pady=(24, 12))
        top.pack_propagate(False)

        mark = tk.Canvas(top, width=48, height=48, bg=COLOR_BG, highlightthickness=0)
        mark.pack(side="left", pady=5)
        mark.create_rectangle(4, 5, 44, 43, outline=COLOR_ACCENT, width=2)
        mark.create_line(12, 16, 36, 16, fill=COLOR_WHITE, width=2)
        mark.create_rectangle(12, 23, 36, 29, fill=COLOR_BLACK, outline=COLOR_BLACK)
        mark.create_line(12, 36, 29, 36, fill=COLOR_WHITE, width=2)

        title_group = tk.Frame(top, bg=COLOR_BG)
        title_group.pack(side="left", padx=(14, 0))
        tk.Label(
            title_group,
            text=APP_TITLE,
            bg=COLOR_BG,
            fg=COLOR_WHITE,
            font=("Noto Sans JP", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_group,
            text="検出した領域を画像から削除します。共有前に目視確認してください",
            bg=COLOR_BG,
            fg=COLOR_MUTED,
            font=("Noto Sans JP", 10),
        ).pack(anchor="w", pady=(2, 0))

        privacy = tk.Label(
            top,
            text="オフライン処理",
            bg="#123A3A",
            fg="#8EF2E5",
            font=("Noto Sans JP", 9, "bold"),
            padx=12,
            pady=7,
        )
        privacy.pack(side="right", pady=10)

        body = tk.Frame(self, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=38, pady=(0, 28))

        rail = tk.Frame(body, bg=COLOR_PANEL, width=220)
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)
        tk.Label(
            rail,
            text="処理の流れ",
            bg=COLOR_PANEL,
            fg=COLOR_WHITE,
            font=("Noto Sans JP", 12, "bold"),
        ).pack(anchor="w", padx=24, pady=(26, 24))

        self.step_labels: list[tk.Label] = []
        for number, heading, note in [
            (1, "PDFを確認", "CIC帳票の構造を照合"),
            (2, "削除領域を画像化", "未認識ページは全面黒塗り"),
            (3, "PDF構造を検証", "保存後に目視確認が必要"),
        ]:
            row = tk.Frame(rail, bg=COLOR_PANEL)
            row.pack(fill="x", padx=22, pady=(0, 24))
            badge = tk.Label(
                row,
                text=str(number),
                width=3,
                height=1,
                bg=COLOR_PANEL_2,
                fg=COLOR_MUTED,
                font=("Bahnschrift", 11),
                pady=5,
            )
            badge.pack(side="left", anchor="n")
            copy = tk.Frame(row, bg=COLOR_PANEL)
            copy.pack(side="left", padx=(12, 0), fill="x", expand=True)
            tk.Label(copy, text=heading, bg=COLOR_PANEL, fg=COLOR_WHITE, font=("Noto Sans JP", 10, "bold")).pack(anchor="w")
            tk.Label(copy, text=note, bg=COLOR_PANEL, fg=COLOR_MUTED, font=("Noto Sans JP", 8), wraplength=138, justify="left").pack(anchor="w", pady=(3, 0))
            self.step_labels.append(badge)

        safety = tk.Frame(rail, bg="#0D2A30")
        safety.pack(side="bottom", fill="x", padx=14, pady=14)
        tk.Label(
            safety,
            text="元PDFは変更しません",
            bg="#0D2A30",
            fg="#A8F4E9",
            font=("Noto Sans JP", 9, "bold"),
        ).pack(anchor="w", padx=14, pady=(13, 3))
        tk.Label(
            safety,
            text="黒塗りした領域の元データは出力に残りません。検出漏れがないか目視確認が必要です。保存先は同期しないローカルフォルダを選んでください。",
            bg="#0D2A30",
            fg="#BED5D8",
            font=("Noto Sans JP", 8),
            wraplength=160,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 13))

        main = tk.Frame(body, bg=COLOR_PAPER)
        main.pack(side="left", fill="both", expand=True, padx=(18, 0))

        content = tk.Frame(main, bg=COLOR_PAPER)
        content.pack(fill="both", expand=True, padx=34, pady=30)

        tk.Label(
            content,
            text="CICのPDFを選択",
            bg=COLOR_PAPER,
            fg=COLOR_INK,
            font=("Noto Sans JP", 26, "bold"),
        ).pack(anchor="w")
        tk.Label(
            content,
            text="検出結果を確認して保存します。未認識ページは全面を黒塗りします。",
            bg=COLOR_PAPER,
            fg="#4B5A68",
            font=("Noto Sans JP", 10),
        ).pack(anchor="w", pady=(4, 22))

        self.file_panel = tk.Frame(content, bg="#E9E6DC", highlightbackground="#C9C5BA", highlightthickness=1)
        self.file_panel.pack(fill="x")
        inner = tk.Frame(self.file_panel, bg="#E9E6DC")
        inner.pack(fill="x", padx=20, pady=18)
        self.file_name = tk.Label(
            inner,
            text="PDFが選択されていません",
            bg="#E9E6DC",
            fg=COLOR_INK,
            font=("Noto Sans JP", 11, "bold"),
            anchor="w",
        )
        self.file_name.pack(fill="x")
        self.file_detail = tk.Label(
            inner,
            text="ファイルはアップロードされません",
            bg="#E9E6DC",
            fg="#5B6872",
            font=("Noto Sans JP", 9),
            anchor="w",
        )
        self.file_detail.pack(fill="x", pady=(4, 12))
        self.choose_button = ttk.Button(inner, text="PDFを選ぶ", style="Secondary.TButton", command=self._choose_file)
        self.choose_button.pack(anchor="w")

        self.status_panel = tk.Frame(content, bg=COLOR_PAPER)
        self.status_panel.pack(fill="x", pady=(24, 0))
        self.status_title = tk.Label(
            self.status_panel,
            text="準備中",
            bg=COLOR_PAPER,
            fg=COLOR_INK,
            font=("Noto Sans JP", 11, "bold"),
            wraplength=480,
            justify="left",
            anchor="w",
        )
        self.status_title.pack(anchor="w")
        self.status_text = tk.Label(
            self.status_panel,
            text="PDFを選ぶと、ページと個人情報欄を検査します。",
            bg=COLOR_PAPER,
            fg="#53616D",
            font=("Noto Sans JP", 9),
            wraplength=570,
            justify="left",
        )
        self.status_text.pack(anchor="w", pady=(5, 10))
        self.progress = ttk.Progressbar(self.status_panel, style="Secure.Horizontal.TProgressbar", mode="determinate", maximum=100)
        self.progress.pack(fill="x")

        self.review_panel = tk.Frame(content, bg="#E9E6DC", highlightbackground="#C9C5BA", highlightthickness=1)
        self.review_panel.pack(fill="x", pady=(18, 0))
        tk.Label(
            self.review_panel,
            text="保存前の検出内訳",
            bg="#E9E6DC",
            fg=COLOR_INK,
            font=("Noto Sans JP", 9, "bold"),
        ).pack(anchor="w", padx=14, pady=(10, 3))
        review_body = tk.Frame(self.review_panel, bg="#E9E6DC")
        review_body.pack(fill="both", padx=14, pady=(0, 10))
        self.review_text = tk.Text(
            review_body,
            bg="#E9E6DC",
            fg="#55616A",
            font=("Noto Sans JP", 8),
            height=4, wrap="word", relief="flat", highlightthickness=0,
            state="disabled",
        )
        self.review_scroll = ttk.Scrollbar(review_body, orient="vertical", command=self.review_text.yview)
        self.review_text.configure(yscrollcommand=self.review_scroll.set)
        self.review_text.pack(side="left", fill="both", expand=True)
        self.review_scroll.pack(side="right", fill="y")
        self._set_review_text("PDFを確認すると、ページごとの削除対象をここに表示します。")

        action = tk.Frame(content, bg=COLOR_PAPER)
        action.pack(side="bottom", fill="x", pady=(18, 0))
        action_controls = tk.Frame(action, bg=COLOR_PAPER)
        action_controls.pack(fill="x")
        self.save_button = ttk.Button(
            action_controls,
            text="黒塗りPDFを保存",
            style="Primary.TButton",
            command=self._save_masked,
            state="disabled",
        )
        self.save_button.pack(side="left")
        self.open_button = ttk.Button(
            action_controls,
            text="保存先を表示",
            style="Secondary.TButton",
            command=self._show_output,
            state="disabled",
        )
        self.open_button.pack(side="left", padx=(10, 0))

        self.footer = tk.Label(
            action,
            text="ページ数・順序の制限なし／共有前に目視確認",
            bg=COLOR_PAPER,
            fg="#4B5751",
            font=("Noto Sans JP", 8),
        )
        self.footer.pack(anchor="w", pady=(8, 0))

    def _set_steps(self, completed: int, active: int | None = None) -> None:
        for index, badge in enumerate(self.step_labels, start=1):
            if index <= completed:
                badge.configure(bg=COLOR_ACCENT, fg=COLOR_INK, text="✓")
            elif index == active:
                badge.configure(bg=COLOR_WARNING, fg=COLOR_INK, text=str(index))
            else:
                badge.configure(bg=COLOR_PANEL_2, fg=COLOR_MUTED, text=str(index))

    def _set_review_text(self, text: str) -> None:
        self.review_text.configure(state="normal")
        self.review_text.delete("1.0", "end")
        self.review_text.insert("1.0", text)
        self.review_text.configure(state="disabled")
        self.review_text.yview_moveto(0)

    def _choose_file(self) -> None:
        if self.busy:
            return
        path = filedialog.askopenfilename(
            title="CICのPDFを選択",
            filetypes=[("PDFファイル", "*.pdf")],
        )
        if path:
            self._analyze(Path(path))

    def _request_close(self) -> None:
        if self.busy:
            messagebox.showinfo(APP_TITLE, "処理中は終了できません。保存またはエラーの表示が完了してから閉じてください。")
            return
        if self.worker is not None and self.worker.is_alive():
            self.after(80, self._request_close)
            return
        self.destroy()

    def _start_worker(self, target: Callable[[], None]) -> None:
        self.worker = threading.Thread(target=target, daemon=False)
        self.worker.start()

    def _analyze(self, path: Path) -> None:
        if self.busy:
            return
        self.busy = True
        self.analysis = None
        self.last_output = None
        self.file_name.configure(text=path.name)
        self.file_detail.configure(text=str(path.parent))
        self.status_title.configure(text="帳票を確認しています", fg=COLOR_INK)
        self.status_text.configure(text="レイアウトと個人情報欄の境界を照合しています。")
        self._set_review_text("ページごとのレイアウトと個人情報欄の境界を検査しています。")
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        self.choose_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self._set_steps(0, 1)

        def worker() -> None:
            try:
                result = analyze_document(path)
                self.events.put(("analysis_ok", result))
            except BaseException as exc:
                self.events.put(("analysis_error", exc))

        self._start_worker(worker)

    def _save_masked(self) -> None:
        if not self.analysis or self.busy:
            return
        suggested = self.analysis.input_path.with_name(f"{self.analysis.input_path.stem}_masked.pdf")
        path = filedialog.asksaveasfilename(
            title="削除済みPDFを保存",
            defaultextension=".pdf",
            initialdir=str(suggested.parent),
            initialfile=suggested.name,
            filetypes=[("PDFファイル", "*.pdf")],
        )
        if not path:
            return

        try:
            output = _local_path(path)
        except (ValueError, OSError):
            messagebox.showwarning(APP_TITLE, "同期しないローカル固定ディスクのフォルダを選んでください。共有・リンク・同期フォルダは使用できません。")
            return
        if output == self.analysis.input_path or (output.exists() and os.path.samefile(output, self.analysis.input_path)):
            messagebox.showwarning(APP_TITLE, "元のPDFは上書きできません。別のファイル名を指定してください。")
            return

        self.busy = True
        self.status_title.configure(text="削除領域を画像化しています", fg=COLOR_INK)
        self.status_text.configure(text="変換中はアプリを閉じないでください。")
        self.progress.stop()
        self.progress.configure(mode="determinate", value=0)
        self.choose_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self._set_steps(1, 2)

        def report(done: int, total: int, text: str) -> None:
            self.events.put(("progress", (done, total, text)))

        def worker() -> None:
            try:
                result = process_document(self.analysis, output, report)
                self.events.put(("process_ok", result))
            except BaseException as exc:
                self.events.put(("process_error", exc))

        self._start_worker(worker)

    def _poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "analysis_ok":
                    self._on_analysis_ok(payload)
                elif event == "analysis_error":
                    self._on_error(payload, during_analysis=True)
                elif event == "progress":
                    done, total, text = payload
                    self.progress.configure(value=(done / total * 100 if total else 0))
                    self.status_text.configure(text=text)
                    self._set_steps(1 if done < total else 2, 2 if done < total else 3)
                elif event == "process_ok":
                    self._on_process_ok(payload)
                elif event == "process_error":
                    self._on_error(payload, during_analysis=False)
        except Empty:
            pass
        self.after(80, self._poll_events)

    def _on_analysis_ok(self, analysis: Analysis) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate", value=100)
        self.analysis = analysis
        self.busy = False
        self.choose_button.configure(state="normal")
        self.save_button.configure(state="normal")
        if analysis.unrecognized_page_count:
            self.status_title.configure(text="未認識ページは全面黒塗りで保存します", fg="#8A5A00")
        else:
            self.status_title.configure(text="削除候補の領域を検出しました", fg=COLOR_ACCENT_DARK)
        detail = (f"{analysis.page_count}ページ、黒塗り{analysis.masked_region_count}か所。"
                  f"全面黒塗り{analysis.fully_masked_page_count}ページ（未認識{analysis.unrecognized_page_count}）。")
        if any(plan.layout in {"application", "usage"} for plan in analysis.plans):
            detail += " " + NAME_ONLY_NOTICE
        if not any(plan.layout in {"application", "usage"} for plan in analysis.plans):
            detail += " 保存後、共有前に全ページを目視確認してください。"
        self.status_text.configure(text=detail)
        self.file_detail.configure(
            text=f"{analysis.page_count}ページ  /  削除対象 {analysis.masked_region_count}か所"
        )
        rows = []
        for plan in analysis.plans:
            categories = []
            for region in plan.regions:
                if region.category not in categories:
                    categories.append(region.category)
            layout_name = LAYOUT_NAMES.get(plan.layout, plan.layout)
            if plan.regions:
                detail = "・".join(categories[:3])
                if len(categories) > 3:
                    detail += " ほか"
                rows.append(
                    f"{plan.page_index + 1}頁｜{layout_name}｜{len(plan.regions)}か所｜{detail}"
                )
            elif plan.layout == "unrecognized":
                rows.append(f"{plan.page_index + 1}頁｜未認識｜全面黒塗り")
            else:
                rows.append(
                    f"{plan.page_index + 1}頁｜{layout_name}｜削除候補なし（目視確認が必要）"
                )
        self._set_review_text("\n".join(rows))
        self._set_steps(1)

    def _on_process_ok(self, result: ProcessResult) -> None:
        self.busy = False
        self.last_output = result.output_path
        self.progress.configure(value=100)
        self.choose_button.configure(state="normal")
        self.save_button.configure(state="normal")
        self.open_button.configure(state="normal")
        title = "保存・PDF構造の検証が完了しました（目視確認が必要）"
        self.status_title.configure(text=title, fg=COLOR_ACCENT_DARK)
        size_mb = result.output_size / (1024 * 1024)
        text = (f"{result.masked_region_count}領域を黒塗りし、文字層・添付・メタデータなどが残っていないことを確認しました。"
                f" 出力サイズ: {size_mb:.1f} MB")
        if result.unrecognized_page_count:
            text += f" 未認識 {result.unrecognized_page_count}ページは全面黒塗りです。"
        text += f" 全面黒塗りは計 {result.fully_masked_page_count}ページ。共有前に削除漏れを目視確認してください。"
        name_only_notice = (NAME_ONLY_NOTICE if self.analysis and any(
            plan.layout in {"application", "usage"} for plan in self.analysis.plans
        ) else "")
        if name_only_notice:
            text += " " + name_only_notice
        self.status_text.configure(text=text)
        self.file_detail.configure(text=str(result.output_path))
        self._set_steps(3)
        messagebox.showinfo(APP_TITLE, f"黒塗りPDFを保存し、PDF構造を検証しました。\n"
                           f"全面黒塗り: {result.fully_masked_page_count}ページ（未認識: {result.unrecognized_page_count}ページ）。\n"
                           "元のPDFは変更していません。\n認識済みのページも、共有前に削除漏れを目視確認してください。")

    def _on_error(self, exc: object, during_analysis: bool) -> None:
        self.busy = False
        self.progress.stop()
        self.progress.configure(mode="determinate", value=0)
        self.choose_button.configure(state="normal")
        self.save_button.configure(state="disabled" if during_analysis else "normal")
        self.status_title.configure(text="安全に処理できませんでした", fg="#A92626")
        message = str(exc) if isinstance(exc, (UnsupportedDocumentError, ValueError, RuntimeError)) else "処理を完了できませんでした。保存先の空き容量・権限を確認し、PDFを選び直してください。"
        self.status_text.configure(text=message)
        if during_analysis:
            self._set_review_text("検出内訳を表示できません。別のPDFを選択してください。")
        self._set_steps(0)
        messagebox.showerror(APP_TITLE, message)

    def _show_output(self) -> None:
        if not self.last_output:
            return
        try:
            subprocess.Popen(["explorer.exe", f"/select,{self.last_output}"])
        except OSError:
            messagebox.showinfo(APP_TITLE, str(self.last_output))


def _run_cli(args: list[str]) -> int:
    show_path = "--show-path" in args
    args = [arg for arg in args if arg != "--show-path"]
    if len(args) != 2:
        print("Usage: cic_masker.py --cli INPUT.pdf OUTPUT.pdf [--show-path]", file=sys.stderr)
        return 2
    try:
        analysis = analyze_document(args[0])
        result = process_document(analysis, args[1], lambda n, total, msg: print(f"[{n}/{total}] {msg}"))
    except (UnsupportedDocumentError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("処理を完了できませんでした。入力PDFと保存先の権限・容量を確認してください。", file=sys.stderr)
        return 1
    print(
        f"OK pages={result.page_count} regions={result.masked_region_count} "
        f"full_mask_pages={result.fully_masked_page_count} bytes={result.output_size}"
    )
    print("PDF構造の検証が完了しました。共有前に画像内の削除漏れを目視確認してください。")
    if any(plan.layout in {"application", "usage"} for plan in analysis.plans):
        print(NAME_ONLY_NOTICE)
    if show_path:
        print(f"output={result.output_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--cli":
        raise SystemExit(_run_cli(sys.argv[2:]))
    app = CICMaskerApp()
    app.mainloop()
