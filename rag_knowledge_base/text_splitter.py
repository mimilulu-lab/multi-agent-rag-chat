"""
文本分块器 - 将长文档分割成适合处理的片段
支持多种分割策略
"""
from typing import List, Callable, Optional
import re
from dataclasses import dataclass

from .document_loader import Document


@dataclass
class TextChunk:
    """文本块对象"""
    content: str
    metadata: dict
    index: int  # 块序号


class TextSplitter:
    """文本分块器基类"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separator: str = "\n",
    ):
        """
        Args:
            chunk_size: 每个块的最大字符数
            chunk_overlap: 块之间的重叠字符数
            separator: 分割符
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def split(self, documents: List[Document]) -> List[TextChunk]:
        """分割文档列表"""
        chunks = []

        for doc in documents:
            doc_chunks = self._split_document(doc)
            chunks.extend(doc_chunks)

        return chunks

    def _split_document(self, document: Document) -> List[TextChunk]:
        """分割单个文档"""
        text = document.content

        # 如果文本长度小于 chunk_size，直接返回
        if len(text) <= self.chunk_size:
            return [TextChunk(
                content=text,
                metadata=document.metadata.copy(),
                index=0
            )]

        # 分割文本
        chunks = self._split_text(text)

        # 包装为 TextChunk
        return [
            TextChunk(
                content=chunk,
                metadata={
                    **document.metadata,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                },
                index=i
            )
            for i, chunk in enumerate(chunks)
        ]

    def _split_text(self, text: str) -> List[str]:
        """核心分割逻辑"""
        # 按分隔符分割
        splits = text.split(self.separator)

        chunks = []
        current_chunk = []
        current_length = 0

        for split in splits:
            split_length = len(split)

            # 如果当前分割加上分隔符会超出限制
            if current_length + split_length + len(self.separator) > self.chunk_size:
                # 保存当前块
                if current_chunk:
                    chunks.append(self.separator.join(current_chunk))

                # 保留重叠部分
                if self.chunk_overlap > 0 and current_chunk:
                    # 从后往前找重叠
                    overlap_text = ""
                    overlap_splits = []
                    for s in reversed(current_chunk):
                        if len(overlap_text) + len(s) + len(self.separator) <= self.chunk_overlap:
                            overlap_splits.insert(0, s)
                            overlap_text = self.separator.join(overlap_splits)
                        else:
                            break
                    current_chunk = overlap_splits
                    current_length = len(overlap_text)
                else:
                    current_chunk = []
                    current_length = 0

            # 添加当前分割
            current_chunk.append(split)
            current_length += split_length + len(self.separator)

        # 保存最后一个块
        if current_chunk:
            chunks.append(self.separator.join(current_chunk))

        return chunks


class RecursiveTextSplitter(TextSplitter):
    """
    递归文本分块器
    优先按段落分割，如果段落太长再按句子，最后按字符
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.separators = separators or ["\n\n", "\n", "。", "；", " ", ""]

    def _split_text(self, text: str) -> List[str]:
        """递归分割文本"""
        return self._recursive_split(text, 0)

    def _recursive_split(self, text: str, separator_index: int) -> List[str]:
        """递归分割"""
        # 如果文本长度小于限制，直接返回
        if len(text) <= self.chunk_size:
            return [text]

        # 如果没有更多分隔符，强制切割
        if separator_index >= len(self.separators):
            return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        separator = self.separators[separator_index]

        # 按当前分隔符分割
        if separator:
            splits = text.split(separator)
        else:
            # 最后一个分隔符是空字符串，按字符分割
            splits = list(text)

        # 合并分割结果
        chunks = []
        current_chunk = []
        current_length = 0

        for split in splits:
            split_length = len(split)
            separator_length = len(separator) if separator else 0

            # 检查是否会超出限制
            if current_length + split_length + separator_length > self.chunk_size:
                if current_chunk:
                    # 保存当前块
                    if separator:
                        chunk_text = separator.join(current_chunk)
                    else:
                        chunk_text = "".join(current_chunk)
                    chunks.append(chunk_text)

                # 递归处理剩余部分
                remaining_text = split if separator else split
                if len(remaining_text) > self.chunk_size:
                    # 需要更细粒度的分割
                    sub_chunks = self._recursive_split(remaining_text, separator_index + 1)
                    chunks.extend(sub_chunks[:-1] if sub_chunks else [])
                    # 最后一个子块作为当前块的开始
                    if sub_chunks:
                        last_sub = sub_chunks[-1]
                        if separator:
                            current_chunk = last_sub.split(separator)
                        else:
                            current_chunk = list(last_sub)
                        current_length = len(last_sub)
                    else:
                        current_chunk = []
                        current_length = 0
                else:
                    current_chunk = [split] if separator else list(split)
                    current_length = split_length
            else:
                current_chunk.append(split)
                current_length += split_length + separator_length

        # 保存最后一个块
        if current_chunk:
            if separator:
                chunks.append(separator.join(current_chunk))
            else:
                chunks.append("".join(current_chunk))

        # 处理重叠
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)

        return chunks

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """添加块间重叠"""
        if not chunks or len(chunks) < 2:
            return chunks

        result = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i-1]
            current_chunk = chunks[i]

            # 计算重叠文本
            overlap_start = max(0, len(prev_chunk) - self.chunk_overlap)
            overlap_text = prev_chunk[overlap_start:]

            # 合并到当前块
            result.append(overlap_text + current_chunk)

        return result


class MarkdownSplitter(RecursiveTextSplitter):
    """
    Markdown 专用分块器
    优先按标题层级分割，保持文档结构
    """

    def _split_document(self, document: Document) -> List[TextChunk]:
        """按 Markdown 结构分割"""
        text = document.content
        headers = document.metadata.get('headers', [])

        if not headers:
            # 如果没有标题信息，回退到普通递归分割
            return super()._split_document(document)

        # 按标题分割
        chunks = []
        current_section = []
        current_header = None

        lines = text.split('\n')
        current_line = 0

        for line in lines:
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if header_match:
                # 保存上一个章节
                if current_section:
                    section_text = '\n'.join(current_section)
                    if len(section_text) > self.chunk_size:
                        # 章节太长，需要进一步分割
                        sub_chunks = self._split_text(section_text)
                        for i, sub_chunk in enumerate(sub_chunks):
                            chunks.append(TextChunk(
                                content=sub_chunk,
                                metadata={
                                    **document.metadata,
                                    'header': current_header,
                                    'chunk_index': i,
                                },
                                index=len(chunks)
                            ))
                    else:
                        chunks.append(TextChunk(
                            content=section_text,
                            metadata={
                                **document.metadata,
                                'header': current_header,
                                'chunk_index': 0,
                            },
                            index=len(chunks)
                        ))

                # 开始新章节
                current_header = header_match.group(2).strip()
                current_section = [line]
            else:
                current_section.append(line)

        # 保存最后一个章节
        if current_section:
            section_text = '\n'.join(current_section)
            if len(section_text) > self.chunk_size:
                sub_chunks = self._split_text(section_text)
                for i, sub_chunk in enumerate(sub_chunks):
                    chunks.append(TextChunk(
                        content=sub_chunk,
                        metadata={
                            **document.metadata,
                            'header': current_header,
                            'chunk_index': i,
                        },
                        index=len(chunks)
                    ))
            else:
                chunks.append(TextChunk(
                    content=section_text,
                    metadata={
                        **document.metadata,
                        'header': current_header,
                        'chunk_index': 0,
                    },
                    index=len(chunks)
                ))

        # 更新 total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.metadata['total_chunks'] = total

        return chunks


# 便捷函数
def split_documents(
    documents: List[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    splitter_type: str = "recursive"
) -> List[TextChunk]:
    """
    便捷函数：分割文档

    Args:
        documents: 文档列表
        chunk_size: 块大小
        chunk_overlap: 重叠大小
        splitter_type: 分割器类型 ("simple", "recursive", "markdown")

    Returns:
        TextChunk 列表
    """
    if splitter_type == "markdown":
        splitter = MarkdownSplitter(chunk_size, chunk_overlap)
    elif splitter_type == "recursive":
        splitter = RecursiveTextSplitter(chunk_size, chunk_overlap)
    else:
        splitter = TextSplitter(chunk_size, chunk_overlap)

    return splitter.split(documents)
