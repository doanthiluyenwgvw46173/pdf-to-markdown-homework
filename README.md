# PDF to Markdown Homework Script

四明山夜校第四期作业：一个把 PDF 转成 Markdown 初稿的 Python 实用脚本。

## 功能

- 支持单个 PDF 转换为 Markdown；
- 支持文件夹批量转换，可选递归处理子文件夹；
- 按 PDF 页码生成 `### 第 N 页` 标题，便于回看原文；
- 在 Markdown 开头记录来源 PDF、转换时间、转换引擎、总页数；
- 默认不覆盖已有 Markdown，避免误操作；
- 支持 `pypdf` 和 `pdfplumber` 两种文字抽取引擎。

> 注意：本脚本适合可复制文字型 PDF。扫描件、签章、金额、日期、页码、复杂表格仍需要人工核对原 PDF。

## 安装依赖

```bash
python3 -m pip install pypdf pdfplumber
```

## 使用方法

### 转换单个 PDF

```bash
python3 pdf_to_markdown.py sample_input.pdf -o sample_output.md --overwrite
```

### 转换文件夹中的 PDF

```bash
python3 pdf_to_markdown.py ./pdf_files -o ./markdown_files
```

### 递归转换子文件夹

```bash
python3 pdf_to_markdown.py ./pdf_files -o ./markdown_files --recursive
```

## 参数说明

| 参数 | 说明 |
| --- | --- |
| `input` | PDF 文件路径，或包含 PDF 的文件夹路径 |
| `-o, --output` | 输出 Markdown 文件或输出文件夹 |
| `--recursive` | 输入为文件夹时，递归处理子文件夹 |
| `--overwrite` | 允许覆盖已有 Markdown 输出文件 |
| `--engine` | 选择抽取引擎：`auto`、`pypdf`、`pdfplumber` |

## 测试

本仓库包含一个样例 PDF：`sample_input.pdf`。运行：

```bash
python3 pdf_to_markdown.py sample_input.pdf -o sample_output.md --overwrite
```

可以生成 `sample_output.md`。

## 局限性

- 扫描版 PDF 需要先 OCR；
- 复杂表格、脚注、页眉页脚可能需要人工整理；
- 法律材料中的金额、日期、当事人名称、页码引用必须人工复核。
