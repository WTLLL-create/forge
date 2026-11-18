"""Bounded read-only extraction. No OCR, formula evaluation, or imputation."""
from datetime import date, datetime, time
import io
import json
import math
import zipfile


class InputExtractionError(ValueError):
    """Only locally defined codes may escape into the execution manifest."""


def extract_pdf(data):
    try:
        import pypdf
    except ImportError:
        raise InputExtractionError('PDF_DEPENDENCY_MISSING') from None
    try:
        if not data.startswith(b'%PDF-') or b'%%EOF' not in data[-2048:]:
            raise InputExtractionError('PDF_PARSE_ERROR')
        reader = pypdf.PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise InputExtractionError('PDF_ENCRYPTED')
        if not 0 < len(reader.pages) <= 100:
            raise InputExtractionError('PDF_SIZE_LIMIT')
        segments = {}
        count = 0
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            if not text.strip():
                # Includes blank and image-only pages; never silently omit a page.
                raise InputExtractionError('PDF_TEXT_UNAVAILABLE')
            count += len(text)
            if count > 60_000:
                raise InputExtractionError('INPUT_CONTEXT_BUDGET_EXCEEDED')
            for line, value in enumerate(text.splitlines(), 1):
                if value.strip():
                    segments[f'P{number}:L{line}'] = value
        return segments, {'parser': 'pypdf', 'parser_version': pypdf.__version__,
                          'format_version': 'pdf-page-lines/v1', 'page_count': len(reader.pages),
                          'visual_review': 'PENDING', 'ocr_performed': False}
    except InputExtractionError:
        raise
    except Exception:
        raise InputExtractionError('PDF_PARSE_ERROR') from None


def extract_xlsx(data):
    try:
        import openpyxl
    except ImportError:
        raise InputExtractionError('XLSX_DEPENDENCY_MISSING') from None
    book = None
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 2048 or sum(e.file_size for e in entries) > 50_000_000:
                raise InputExtractionError('XLSX_SIZE_LIMIT')
            # Never accept active content disguised as an ordinary workbook.
            if any('vbaproject' in e.filename.lower() or e.filename.startswith('xl/externalLinks/') for e in entries):
                raise InputExtractionError('XLSX_ACTIVE_CONTENT_UNSUPPORTED')
        book = openpyxl.load_workbook(io.BytesIO(data), read_only=False,
                                      data_only=False, keep_links=False)
        if not 0 < len(book.worksheets) <= 16:
            raise InputExtractionError('XLSX_SIZE_LIMIT')
        sheets, segments = [], {}
        total, chars = 0, 0
        for index, sheet in enumerate(book.worksheets, 1):
            total += sheet.max_row * sheet.max_column
            if sheet.max_row > 10000 or sheet.max_column > 256 or total > 100000:
                raise InputExtractionError('XLSX_SIZE_LIMIT')
            cells = []
            for row in sheet.iter_rows():
                for cell in row:
                    value = cell.value
                    if value is None:
                        kind = 'blank'
                    elif cell.data_type == 'f':
                        if not isinstance(value, str):
                            raise InputExtractionError('XLSX_FORMULA_UNSUPPORTED')
                        kind = 'formula'
                    elif cell.data_type == 'e':
                        kind = 'error'
                    elif isinstance(value, bool):
                        kind = 'boolean'
                    elif isinstance(value, (datetime, date, time)):
                        kind, value = 'datetime', value.isoformat()
                    elif isinstance(value, (int, float)):
                        if not math.isfinite(value):
                            raise InputExtractionError('XLSX_NONFINITE')
                        kind = 'number'
                    elif isinstance(value, str):
                        kind = 'text'
                    else:
                        raise InputExtractionError('XLSX_CELL_TYPE_UNSUPPORTED')
                    locator = f'S{index}!{cell.coordinate}'
                    text = json.dumps(value, ensure_ascii=False)
                    chars += len(text)
                    if chars > 60_000:
                        raise InputExtractionError('INPUT_CONTEXT_BUDGET_EXCEEDED')
                    segments[locator] = text
                    cells.append({'coordinate': cell.coordinate, 'kind': kind, 'value': value,
                                  'number_format': cell.number_format})
            sheets.append({'sheet_id': f'S{index}', 'name': sheet.title, 'state': sheet.sheet_state,
                           'rows': sheet.max_row, 'columns': sheet.max_column, 'cells': cells,
                           'merged_ranges': sorted(str(r) for r in sheet.merged_cells.ranges)})
        return segments, {'parser': 'openpyxl', 'parser_version': openpyxl.__version__,
                          'format_version': 'xlsx-cells/v1', 'sheets': sheets,
                          'formula_evaluation': 'NOT_PERFORMED', 'semantic_review': 'PENDING'}
    except InputExtractionError:
        raise
    except Exception:
        raise InputExtractionError('XLSX_PARSE_ERROR') from None
    finally:
        if book is not None:
            book.close()
