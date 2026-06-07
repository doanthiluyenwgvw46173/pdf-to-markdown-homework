#!/usr/bin/env python3
"""
pdf_to_markdown.py

把可复制文字型 PDF 转换成 Markdown 初稿。
- 支持单个 PDF 或整个文件夹批量转换
- 默认不覆盖已有 Markdown
- 自动按页生成标题，方便回看原 PDF 页码

注意：扫描件、签章、复杂表格、金额和日期仍需人工核对原件。
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, List, Tuple

PageTexts = List[str]


def normalize_text(raw: str) -> str:
    """把 PDF 抽取出来的文字整理成相对干净的 Markdown 段落。"""
    raw = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in raw.split("\n")]

    cleaned: list[str] = []
    previous_blank = False
    for line in lines:
        line = line.strip()
        if not line:
            if not previous_blank:
                cleaned.append("")
            previous_blank = True
            continue
        cleaned.append(line)
        previous_blank = False

    text = "\n".join(cleaned).strip()
    if not text:
        return "_本页没有提取到可复制文字，可能是扫描件；如需完整转换，请先做 OCR。_"
    return text


def extract_with_pypdf(pdf_path: Path) -> Tuple[PageTexts, dict]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on local env
        raise RuntimeError("未安装 pypdf，请先运行：python3 -m pip install pypdf") from exc

    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # pragma: no cover - depends on PDF
            raise RuntimeError("PDF 已加密，且无法用空密码解密。请先解除密码后再转换。") from exc

    pages = [normalize_text(page.extract_text() or "") for page in reader.pages]
    metadata = {}
    if reader.metadata:
        metadata = {str(k).strip("/"): str(v) for k, v in reader.metadata.items() if v}
    return pages, metadata


def extract_with_pdfplumber(pdf_path: Path) -> Tuple[PageTexts, dict]:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - depends on local env
        raise RuntimeError("未安装 pdfplumber，请先运行：python3 -m pip install pdfplumber") from exc

    pages: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            pages.append(normalize_text(page.extract_text() or ""))
        metadata = dict(pdf.metadata or {})
    return pages, metadata


def extract_pages(pdf_path: Path, engine: str) -> Tuple[PageTexts, dict, str]:
    """按指定引擎抽取；auto 模式先 pypdf，失败后再 pdfplumber。"""
    engines: list[tuple[str, Callable[[Path], Tuple[PageTexts, dict]]]]
    if engine == "pypdf":
        engines = [("pypdf", extract_with_pypdf)]
    elif engine == "pdfplumber":
        engines = [("pdfplumber", extract_with_pdfplumber)]
    else:
        engines = [("pypdf", extract_with_pypdf), ("pdfplumber", extract_with_pdfplumber)]

    errors: list[str] = []
    for name, func in engines:
        try:
            pages, metadata = func(pdf_path)
            return pages, metadata, name
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    raise RuntimeError("所有 PDF 抽取引擎均失败：\n" + "\n".join(errors))


def markdown_escape_inline(text: str) -> str:
    return text.replace("`", "\\`")


def build_markdown(pdf_path: Path, pages: PageTexts, metadata: dict, engine_name: str) -> str:
    title = metadata.get("Title") or pdf_path.stem
    converted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md: list[str] = []
    md.append(f"# {title}")
    md.append("")
    md.append("> [!info] 转换说明")
    md.append(f"> - 来源 PDF：`{markdown_escape_inline(str(pdf_path))}`")
    md.append(f"> - 转换时间：{converted_at}")
    md.append(f"> - 转换引擎：{engine_name}")
    md.append(f"> - 总页数：{len(pages)}")
    md.append("> - 注意：自动提取只适合生成 Markdown 初稿；扫描件、签章、金额、日期、页码和复杂表格请回看原 PDF 人工复核。")
    md.append("")

    if metadata:
        md.append("## PDF 元数据")
        md.append("")
        for key in sorted(metadata):
            md.append(f"- **{key}**：{metadata[key]}")
        md.append("")

    md.append("## 正文")
    md.append("")
    for index, page_text in enumerate(pages, start=1):
        md.append(f"### 第 {index} 页")
        md.append("")
        md.append(page_text)
        md.append("")
    return "\n".join(md).rstrip() + "\n"


def iter_pdfs(input_path: Path, recursive: bool) -> Iterable[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            raise ValueError(f"输入文件不是 PDF：{input_path}")
        yield input_path
        return

    pattern = "**/*.pdf" if recursive else "*.pdf"
    yield from sorted(input_path.glob(pattern))


def decide_output_path(pdf_path: Path, input_root: Path, output: Path | None, recursive: bool) -> Path:
    if output is None:
        return pdf_path.with_suffix(".md")

    # 单文件 + 输出路径带 .md 后缀：直接写到该文件
    if input_root.is_file() and output.suffix.lower() == ".md":
        return output

    # 文件夹输出：保留递归时的相对目录结构
    if input_root.is_dir() and recursive:
        relative_pdf = pdf_path.relative_to(input_root)
        return (output / relative_pdf).with_suffix(".md")

    return output / f"{pdf_path.stem}.md"


def convert_one(pdf_path: Path, input_root: Path, output: Path | None, recursive: bool, overwrite: bool, engine: str) -> Path:
    output_path = decide_output_path(pdf_path, input_root, output, recursive)
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在，为避免覆盖已跳过：{output_path}；如需覆盖请加 --overwrite")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pages, metadata, engine_name = extract_pages(pdf_path, engine)
    markdown = build_markdown(pdf_path, pages, metadata, engine_name)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把可复制文字型 PDF 转换成 Markdown 初稿。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", help="PDF 文件路径，或包含 PDF 的文件夹路径")
    parser.add_argument("-o", "--output", help="输出 Markdown 文件或输出文件夹；不填则与 PDF 同目录")
    parser.add_argument("--recursive", action="store_true", help="输入为文件夹时，递归处理子文件夹内的 PDF")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖已存在的 Markdown 输出文件")
    parser.add_argument("--engine", choices=["auto", "pypdf", "pdfplumber"], default="auto", help="PDF 文本抽取引擎")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    input_path = Path(args.input).expanduser()
    output = Path(args.output).expanduser() if args.output else None

    if not input_path.exists():
        print(f"错误：输入路径不存在：{input_path}", file=sys.stderr)
        return 2

    pdfs = list(iter_pdfs(input_path, args.recursive))
    if not pdfs:
        print(f"没有找到 PDF 文件：{input_path}", file=sys.stderr)
        return 1

    print(f"发现 {len(pdfs)} 个 PDF，开始转换……")
    success = 0
    for pdf in pdfs:
        try:
            out = convert_one(pdf, input_path, output, args.recursive, args.overwrite, args.engine)
            success += 1
            print(f"[OK] {pdf} -> {out}")
        except Exception as exc:
            print(f"[FAIL] {pdf}: {exc}", file=sys.stderr)

    print(f"完成：成功 {success}/{len(pdfs)} 个。")
    return 0 if success == len(pdfs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
