"""Synthetic privacy regressions: no real report, identity, or external fixture."""
from __future__ import annotations

import io
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock
from contextlib import redirect_stdout, redirect_stderr

try:
    from . import cic_masker as masker
except ImportError:
    import cic_masker as masker

pymupdf = masker.pymupdf


class CICMaskerTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix="cic-synthetic-test-", dir=Path(__file__).resolve().parents[2])
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def summary_page(self, document, rotated=False):
        page = document.new_page(width=595 if rotated else 842, height=842 if rotated else 595)
        if rotated:
            page.set_rotation(90)
        transform = page.derotation_matrix
        for row in range(11):
            page.draw_line(pymupdf.Point(500, 352 + row * 16) * transform,
                           pymupdf.Point(772, 352 + row * 16) * transform, width=0.5)
        for column in (500, 636, 772):
            page.draw_line(pymupdf.Point(column, 352) * transform,
                           pymupdf.Point(column, 512) * transform, width=0.5)
        for row in range(10):
            page.insert_text(pymupdf.Point(506, 363 + row * 16) * transform, f"Field {row}",
                             fontsize=7, rotate=90 if rotated else 0)
            page.insert_text(pymupdf.Point(640, 363 + row * 16) * transform, f"SYNTHETIC_VALUE_{row}",
                             fontsize=7, rotate=90 if rotated else 0)
        page.insert_text(pymupdf.Point(20, 100) * transform, "SYNTHETIC_ADDRESSEE",
                         fontsize=10, rotate=90 if rotated else 0)
        page.insert_text(pymupdf.Point(610, 40) * transform, "12-AB-345678",
                         fontsize=10, rotate=90 if rotated else 0)
        return page

    def make_pdf(self, name="input.pdf", pages=1, summary_index=None, rotated=False, extra=False):
        path = self.root / name
        with pymupdf.open() as document:
            for index in range(pages):
                if index == summary_index:
                    self.summary_page(document, rotated=rotated)
                else:
                    page = document.new_page(width=842, height=595)
                    page.insert_text((30, 30), "SYNTHETIC_PRIVATE_CONTENT", fontsize=12)
            if extra:
                page = document[0]
                page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(20, 20, 100, 40),
                                  "uri": "https://example.invalid/synthetic"})
                page.add_text_annot((150, 50), "SYNTHETIC_ANNOTATION")
                widget = pymupdf.Widget()
                widget.field_name = "SYNTHETIC_FIELD"
                widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
                widget.field_value = "SYNTHETIC_WIDGET_VALUE"
                widget.rect = pymupdf.Rect(200, 20, 300, 50)
                page.add_widget(widget)
                document.embfile_add("synthetic.txt", b"SYNTHETIC_ATTACHMENT")
                document.set_metadata({"author": "SYNTHETIC_AUTHOR", "title": "SYNTHETIC_TITLE"})
                document.set_xml_metadata('<x:xmpmeta xmlns:x="adobe:ns:meta/">SYNTHETIC_XML</x:xmpmeta>')
                document.set_toc([[1, "SYNTHETIC_OUTLINE", 1]])
                document.xref_set_key(document.pdf_catalog(), "OpenAction",
                                      "<< /S /JavaScript /JS (SYNTHETIC_ACTION) >>")
            document.save(path)
        return path

    def convert(self, path, name="output.pdf"):
        analysis = masker.analyze_document(path)
        result = masker.process_document(analysis, self.root / name)
        return analysis, result

    def assert_black(self, page, rectangle=None):
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False, clip=rectangle)
        self.assertEqual(set(pixmap.samples), {0})

    def test_reordered_summary_masks_every_value(self):
        path = self.make_pdf(pages=2, summary_index=1)
        analysis, result = self.convert(path)
        self.assertEqual([plan.layout for plan in analysis.plans], ["unrecognized", "summary"])
        self.assertEqual(analysis.fully_masked_page_count, 1)
        self.assertGreaterEqual(len(analysis.plans[1].regions), 12)
        with pymupdf.open(result.output_path) as document:
            self.assert_black(document[0])
            self.assert_black(document[1], pymupdf.Rect(638, 354, 769, 509))
            self.assert_black(document[1], pymupdf.Rect(10, 90, 175, 135))
            self.assertNotEqual(set(document[1].get_pixmap(clip=pymupdf.Rect(200, 200, 220, 220)).samples), {0})

    def test_summary_geometry_is_page_order_independent_when_rotated(self):
        path = self.make_pdf(pages=2, summary_index=1, rotated=True)
        analysis, result = self.convert(path)
        self.assertEqual(analysis.plans[1].layout, "summary")
        with pymupdf.open(result.output_path) as document:
            self.assert_black(document[1], pymupdf.Rect(638, 354, 769, 509))
            self.assertEqual(document[1].rect, pymupdf.Rect(0, 0, 842, 595))

    def test_unknown_page_is_full_black_without_source_render(self):
        path = self.make_pdf()
        analysis = masker.analyze_document(path)
        analysis.plans[0].regions.clear()
        with mock.patch.object(pymupdf.Page, "get_pixmap", side_effect=AssertionError("source render")):
            result = masker.process_document(analysis, self.root / "output.pdf")
        with pymupdf.open(result.output_path) as document:
            self.assert_black(document[0])

    def test_large_unknown_page_does_not_allocate_a_large_raster(self):
        path = self.root / "large.pdf"
        with pymupdf.open() as document:
            document.new_page(width=10000, height=10000)
            document.save(path)
        _, result = self.convert(path)
        self.assertLess(result.output_size, 10000)
        with pymupdf.open(result.output_path) as document:
            image = document.extract_image(document[0].get_images()[0][0])
            self.assertEqual((image["width"], image["height"]), (1, 1))

    def test_more_than_48_pages_is_accepted_without_order_limit(self):
        path = self.make_pdf(pages=53, summary_index=40)
        analysis, result = self.convert(path)
        self.assertEqual((analysis.page_count, result.page_count), (53, 53))
        self.assertEqual(analysis.plans[40].layout, "summary")
        self.assertEqual(result.fully_masked_page_count, 52)

    def test_original_and_hardlink_output_are_blocked(self):
        path = self.make_pdf()
        original = path.read_bytes()
        analysis = masker.analyze_document(path)
        with self.assertRaises(ValueError):
            masker.process_document(analysis, path)
        alias = self.root / "hardlink.pdf"
        try:
            os.link(path, alias)
        except PermissionError:
            # Sandboxed Windows can deny hardlink creation; exercise samefile gate.
            alias.write_bytes(original)
            with mock.patch.object(masker.os.path, "samefile", return_value=True):
                with self.assertRaises(ValueError):
                    masker.process_document(analysis, alias)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(alias.read_bytes(), original)
            return
        with self.assertRaises(ValueError):
            masker.process_document(analysis, alias)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(alias.read_bytes(), original)

    def test_old_temporary_filename_collision_preserves_input_and_sentinel(self):
        path = self.make_pdf(name=".report.writing.pdf")
        original = path.read_bytes()
        sentinel = self.root / ".output.writing.pdf"
        sentinel.write_bytes(b"SYNTHETIC_EXISTING_SENTINEL")
        analysis = masker.analyze_document(path)
        masker.process_document(analysis, self.root / "report.pdf")
        masker.process_document(analysis, self.root / "output.pdf")
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(sentinel.read_bytes(), b"SYNTHETIC_EXISTING_SENTINEL")
        self.assertEqual(list(self.root.glob(".cic-masker-*.tmp")), [])

    def test_input_mutation_is_rejected_before_output_creation(self):
        path = self.make_pdf()
        analysis = masker.analyze_document(path)
        self.assertFalse(any(isinstance(value, bytes) for value in vars(analysis).values()))
        path.write_bytes(path.read_bytes() + b"\nSYNTHETIC_MUTATION\n")
        with self.assertRaisesRegex(masker.UnsupportedDocumentError, "変更"):
            masker.process_document(analysis, self.root / "output.pdf")
        self.assertEqual(set(self.root.iterdir()), {path})

    def test_processing_uses_the_checked_snapshot_not_a_second_file_open(self):
        path = self.make_pdf(summary_index=0)
        analysis = masker.analyze_document(path)
        original_read = masker._read_input

        def read_then_replace(file):
            snapshot = original_read(file)
            file.write_bytes(b"SYNTHETIC_INVALID_REPLACEMENT")
            return snapshot

        with mock.patch.object(masker, "_read_input", side_effect=read_then_replace):
            result = masker.process_document(analysis, self.root / "output.pdf")
        with pymupdf.open(result.output_path) as document:
            self.assert_black(document[0], pymupdf.Rect(638, 354, 769, 509))

    def test_verification_failure_writes_no_output_or_temporary(self):
        path = self.make_pdf()
        analysis = masker.analyze_document(path)
        with mock.patch.object(masker, "_verify_pdf", side_effect=RuntimeError("synthetic verify error")):
            with self.assertRaises(RuntimeError):
                masker.process_document(analysis, self.root / "output.pdf")
        self.assertEqual(set(self.root.iterdir()), {path})

    def test_replace_errors_and_keyboard_interrupt_clean_only_owned_temp(self):
        path = self.make_pdf(name=".report.writing.pdf")
        original = path.read_bytes()
        output = self.root / "report.pdf"
        output.write_bytes(b"SYNTHETIC_EXISTING_OUTPUT")
        analysis = masker.analyze_document(path)
        for failure in (OSError("synthetic replace failure"), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__):
                with mock.patch.object(masker.os, "replace", side_effect=failure):
                    with self.assertRaises(type(failure)):
                        masker.process_document(analysis, output)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(output.read_bytes(), b"SYNTHETIC_EXISTING_OUTPUT")
                self.assertEqual(list(self.root.glob(".cic-masker-*.tmp")), [])

    def test_final_write_failure_cleans_temp(self):
        path = self.make_pdf()
        analysis = masker.analyze_document(path)
        with mock.patch.object(masker.os, "fsync", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(OSError):
                masker.process_document(analysis, self.root / "output.pdf")
        self.assertEqual(set(self.root.iterdir()), {path})

    def test_fdopen_failure_closes_the_created_descriptor(self):
        path = self.make_pdf()
        analysis = masker.analyze_document(path)
        real_mkstemp = masker.tempfile.mkstemp
        descriptors = []

        def capture_descriptor(*args, **kwargs):
            result = real_mkstemp(*args, **kwargs)
            descriptors.append(result[0])
            return result

        with mock.patch.object(masker.tempfile, "mkstemp", side_effect=capture_descriptor), \
             mock.patch.object(masker.os, "fdopen", side_effect=OSError("synthetic open failure")):
            with self.assertRaises(OSError):
                masker.process_document(analysis, self.root / "output.pdf")
        for descriptor in descriptors:
            with self.assertRaises(OSError):
                os.fstat(descriptor)
        self.assertEqual(set(self.root.iterdir()), {path})

    def test_cleanup_failure_is_reported(self):
        path = self.make_pdf()
        analysis = masker.analyze_document(path)
        with mock.patch.object(masker.os, "replace", side_effect=OSError("synthetic save error")), \
             mock.patch.object(Path, "unlink", side_effect=PermissionError("synthetic unlink error")):
            with self.assertRaisesRegex(RuntimeError, "後始末"):
                masker.process_document(analysis, self.root / "output.pdf")
        leftovers = list(self.root.glob(".cic-masker-*.tmp"))
        self.assertEqual(len(leftovers), 1)
        self.assertFalse((self.root / "output.pdf").exists())
        leftovers[0].unlink()

    def test_source_actions_attachments_annotations_and_metadata_are_not_copied(self):
        path = self.make_pdf(extra=True)
        _, result = self.convert(path)
        data = result.output_path.read_bytes()
        masker._verify_pdf(data, 1)
        with pymupdf.open(stream=data, filetype="pdf") as document:
            self.assertFalse(document.get_xml_metadata())
            self.assertFalse(document.get_toc())
            self.assertEqual(document.embfile_count(), 0)
            self.assertFalse(document[0].get_text().strip())
            self.assertFalse(document[0].get_links())
            self.assertIsNone(document[0].first_annot)
            self.assertFalse(list(document[0].widgets() or ()))
            self.assertNotIn("SYNTHETIC", "\n".join(document.xref_object(i) for i in range(1, document.xref_length())))

    def test_network_and_device_paths_are_rejected_before_access(self):
        paths = (r"\\server\share\input.pdf", "//server/share/input.pdf",
                 r"\\?\UNC\server\share\input.pdf", r"\\.\NUL", r"\??\C:\input.pdf",
                 "CON.pdf", "NUL.pdf", "PRN.pdf", "AUX.pdf", "COM1.pdf", "LPT1.pdf", "NUL .pdf")
        with mock.patch.object(masker.os, "lstat", side_effect=AssertionError("filesystem probe")), \
             mock.patch.object(Path, "read_bytes", side_effect=AssertionError("file read")):
            for path in paths:
                with self.subTest(path=path), self.assertRaises(ValueError):
                    masker.analyze_document(path)

    @unittest.skipUnless(os.name == "nt", "Windows drive gate")
    def test_mapped_network_drive_is_rejected_before_access(self):
        with mock.patch.object(masker, "_fixed_drive", return_value=False), \
             mock.patch.object(masker.os, "lstat", side_effect=AssertionError("network probe")):
            with self.assertRaises(ValueError):
                masker.analyze_document(r"Z:\synthetic.pdf")

    @unittest.skipUnless(os.name == "nt", "Windows relative-path gate")
    def test_relative_path_from_network_cwd_is_rejected_before_drive_query(self):
        with mock.patch.object(masker.ntpath, "abspath", return_value=r"\\synthetic.invalid\share\input.pdf"), \
             mock.patch.object(masker, "_fixed_drive", side_effect=AssertionError("network drive query")):
            with self.assertRaises(ValueError):
                masker.analyze_document("input.pdf")

    def test_cloud_roots_are_rejected_before_access(self):
        cloud = self.root / "synthetic-sync-root"
        with mock.patch.object(masker, "_cloud_roots", return_value=[cloud]), \
             mock.patch.object(masker.os, "lstat", side_effect=AssertionError("sync probe")):
            with self.assertRaises(ValueError):
                masker.analyze_document(cloud / "input.pdf")

    def test_reparse_point_is_rejected_before_read(self):
        path = self.root / "link" / "input.pdf"
        regular_lstat = masker.os.lstat

        def fake_reparse(component):
            if Path(component) == self.root / "link":
                return SimpleNamespace(st_mode=0o040755, st_file_attributes=0x400)
            return regular_lstat(component)

        with mock.patch.object(masker.os, "lstat", side_effect=fake_reparse), \
             mock.patch.object(Path, "read_bytes", side_effect=AssertionError("link read")):
            with self.assertRaises(ValueError):
                masker.analyze_document(path)

    def test_import_disables_inherited_logs_and_external_runtime_module(self):
        sentinel = self.root / "inherited-log.txt"
        sentinel.write_bytes(b"SYNTHETIC_LOG_SENTINEL")
        external = self.root / "external-runtime.py"
        external.write_text("raise RuntimeError('external runtime must not load')\n", encoding="utf-8")
        environment = dict(os.environ)
        environment.update(PYMUPDF_LOG="path:" + str(sentinel),
                           PYMUPDF_MESSAGE="path:" + str(sentinel), MUPDF_CPPYY=str(external))
        code = ("import os; from work.app import cic_masker; "
                "assert all(x not in os.environ for x in ('PYMUPDF_LOG','PYMUPDF_MESSAGE','MUPDF_CPPYY'))")
        result = subprocess.run([sys.executable, "-B", "-c", code], env=environment,
                                cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sentinel.read_bytes(), b"SYNTHETIC_LOG_SENTINEL")

    def test_cli_hides_paths_by_default_and_requires_visual_review(self):
        path = self.make_pdf()
        output = self.root / "output.pdf"
        stream = io.StringIO()
        with redirect_stdout(stream), redirect_stderr(stream):
            self.assertEqual(masker._run_cli([str(path), str(output)]), 0)
        self.assertNotIn(str(self.root), stream.getvalue())
        self.assertIn("目視確認", stream.getvalue())
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(masker._run_cli([str(path), str(output), "--show-path"]), 0)
        self.assertIn(str(output), stream.getvalue())

    def test_table_extraction_or_bad_cells_fall_back_to_full_mask(self):
        with pymupdf.open() as document:
            page = self.summary_page(document)
            with mock.patch.object(pymupdf.Page, "find_tables", side_effect=RuntimeError("synthetic extraction")):
                self.assertTrue(masker._classify_page(page, 7).full_mask)
            table = SimpleNamespace(bbox=(500, 352, 772, 512),
                                    rows=[SimpleNamespace(cells=[(500, 352, 636, 368), None]) for _ in range(10)])
            with mock.patch.object(pymupdf.Page, "find_tables", return_value=SimpleNamespace(tables=[table])):
                self.assertTrue(masker._classify_page(page, 7).full_mask)

    def test_busy_gui_close_does_not_destroy_window(self):
        fake = SimpleNamespace(busy=True, destroy=mock.Mock())
        with mock.patch.object(masker.messagebox, "showinfo") as dialog:
            masker.CICMaskerApp._request_close(fake)
        dialog.assert_called_once()
        fake.destroy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
