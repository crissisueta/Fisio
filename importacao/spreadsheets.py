import csv
import re
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import PurePosixPath
from typing import Any
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree


class SpreadsheetReadError(ValueError):
    pass


@dataclass
class SpreadsheetData:
    sheet_name: str
    headers: list[str]
    rows: list[dict[str, Any]]


NS_MAIN = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_REL = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def read_spreadsheet(uploaded_file, sheet_name: str = "") -> SpreadsheetData:
    filename = uploaded_file.name.lower()
    content = uploaded_file.read()
    if filename.endswith(".csv"):
        table = _read_csv(content)
        return _table_to_data(table, sheet_name="CSV")
    if filename.endswith(".xlsx"):
        return _read_xlsx(content, sheet_name=sheet_name.strip())
    raise SpreadsheetReadError("Formato não suportado.")


def _read_csv(content: bytes) -> list[list[Any]]:
    text = _decode_csv(content)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return [row for row in csv.reader(StringIO(text), dialect)]


def _decode_csv(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise SpreadsheetReadError("Não foi possível ler o CSV.")


def _read_xlsx(content: bytes, sheet_name: str = "") -> SpreadsheetData:
    openpyxl_data = _read_xlsx_with_openpyxl(content, sheet_name=sheet_name)
    if openpyxl_data is not None:
        return openpyxl_data
    return _read_xlsx_with_stdlib(content, sheet_name=sheet_name)


def _read_xlsx_with_openpyxl(content: bytes, sheet_name: str = "") -> SpreadsheetData | None:
    try:
        from openpyxl import load_workbook
    except ImportError:
        return None

    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise SpreadsheetReadError(f"Não foi possível ler o XLSX: {exc}") from exc

    if sheet_name:
        if sheet_name not in workbook.sheetnames:
            raise SpreadsheetReadError(f"Aba '{sheet_name}' não encontrada.")
        worksheet = workbook[sheet_name]
    else:
        worksheet = workbook[workbook.sheetnames[0]]

    table = [list(row) for row in worksheet.iter_rows(values_only=True)]
    return _table_to_data(table, sheet_name=worksheet.title)


def _read_xlsx_with_stdlib(content: bytes, sheet_name: str = "") -> SpreadsheetData:
    try:
        with ZipFile(BytesIO(content)) as archive:
            sheets = _workbook_sheets(archive)
            if not sheets:
                raise SpreadsheetReadError("Nenhuma aba encontrada no XLSX.")

            selected = _select_sheet(sheets, sheet_name)
            shared_strings = _shared_strings(archive)
            table = _worksheet_rows(archive, selected["path"], shared_strings)
            return _table_to_data(table, sheet_name=selected["name"])
    except BadZipFile as exc:
        raise SpreadsheetReadError("Arquivo XLSX inválido.") from exc


def _workbook_sheets(archive: ZipFile) -> list[dict[str, str]]:
    workbook_root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    rels_root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationships = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_root.findall("r:Relationship", NS_REL)
        if rel.attrib.get("Type", "").endswith("/worksheet")
    }

    sheets = []
    for sheet in workbook_root.findall("x:sheets/x:sheet", NS_MAIN):
        rel_id = sheet.attrib.get(f"{{{OFFICE_REL_NS}}}id")
        target = relationships.get(rel_id)
        if not target:
            continue
        sheets.append(
            {
                "name": sheet.attrib["name"],
                "path": _xlsx_target_path(target),
            }
        )
    return sheets


def _select_sheet(sheets: list[dict[str, str]], sheet_name: str) -> dict[str, str]:
    if not sheet_name:
        return sheets[0]
    for sheet in sheets:
        if sheet["name"].casefold() == sheet_name.casefold():
            return sheet
    raise SpreadsheetReadError(f"Aba '{sheet_name}' não encontrada.")


def _xlsx_target_path(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return str(PurePosixPath("xl") / target)


def _shared_strings(archive: ZipFile) -> list[str]:
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    values = []
    for item in root.findall("x:si", NS_MAIN):
        values.append("".join(item.itertext()))
    return values


def _worksheet_rows(archive: ZipFile, path: str, shared_strings: list[str]) -> list[list[Any]]:
    root = ElementTree.fromstring(archive.read(path))
    rows = []
    for row in root.findall("x:sheetData/x:row", NS_MAIN):
        values: list[Any] = []
        for cell in row.findall("x:c", NS_MAIN):
            column = _cell_column_index(cell.attrib.get("r", "")) or len(values) + 1
            while len(values) < column - 1:
                values.append("")
            values.append(_cell_value(cell, shared_strings))
        rows.append(values)
    return rows


def _cell_column_index(reference: str) -> int | None:
    match = re.match(r"([A-Z]+)", reference.upper())
    if not match:
        return None
    index = 0
    for char in match.group(1):
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index


def _cell_value(cell, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find("x:is", NS_MAIN)
        return "" if inline is None else "".join(inline.itertext())

    value = cell.find("x:v", NS_MAIN)
    if value is None or value.text is None:
        return ""

    raw_value = value.text
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (ValueError, IndexError):
            return raw_value
    if cell_type == "b":
        return raw_value == "1"
    if cell_type in {"str", "e"}:
        return raw_value
    return _coerce_number(raw_value)


def _coerce_number(value: str) -> Any:
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer():
        return int(number)
    return number


def _table_to_data(table: list[list[Any]], sheet_name: str) -> SpreadsheetData:
    normalized_rows = [row for row in table if any(_present(cell) for cell in row)]
    if not normalized_rows:
        raise SpreadsheetReadError("A planilha está vazia.")

    headers = [_string_header(value, index) for index, value in enumerate(normalized_rows[0], start=1)]
    headers = _unique_headers(headers)
    rows = []
    for row in normalized_rows[1:]:
        values = {header: row[index] if index < len(row) else "" for index, header in enumerate(headers)}
        if any(_present(value) for value in values.values()):
            rows.append(values)

    if not rows:
        raise SpreadsheetReadError("A planilha não possui linhas de dados.")
    return SpreadsheetData(sheet_name=sheet_name, headers=headers, rows=rows)


def _string_header(value: Any, index: int) -> str:
    text = "" if value is None else str(value).strip()
    return text or f"coluna_{index}"


def _unique_headers(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    unique = []
    for header in headers:
        count = seen.get(header, 0)
        seen[header] = count + 1
        unique.append(header if count == 0 else f"{header}_{count + 1}")
    return unique


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""

