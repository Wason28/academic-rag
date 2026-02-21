# 学术论文问答系统（RAG）开发提示词
## 详细需求
### 一、后端模块
#### 1. 配置文件 `config.py`
- 定义常量：
  - `UPLOAD_DIR = "uploads"`
  - `CHROMA_PERSIST_DIR = "chroma_db"`
  - `COLLECTION_NAME = "academic_papers"`
  - `CHUNK_SIZE = 1000`
  - `CHUNK_OVERLAP = 200`
  - `TOP_K = 5`
  - `EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"`
  - `DEEPSEEK_API_KEY`（从环境变量加载）
  - `DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"`

#### 2. 嵌入模型封装 `embedding.py`
- 使用 `sentence-transformers` 加载指定模型。
- 提供 `embed_text(text: str) -> List[float]` 和 `embed_documents(texts: List[str]) -> List[List[float]]` 方法。

#### 3. 向量数据库封装 `vector_store.py`
- 初始化Chroma持久化客户端。
- 提供方法：
  - `add_documents(docs: List[Document])`：将LangChain Document对象（包含page_content和metadata）添加到集合。
  - `similarity_search(query: str, k: int) -> List[Document]`：执行相似度检索，返回Document列表。
- 注意：Document的metadata需包含 `source`（文件名）、`page`（页码）。

#### 4. PDF处理器 `pdf_processor.py`
- 函数 `process_pdf(file_path: str, filename: str) -> List[Document]`：
  - 使用 `fitz.open` 打开PDF。
  - 遍历每一页，提取文本（`page.get_text()`）。
  - 记录页码（从1开始）。
  - 将所有文本合并后，使用 `RecursiveCharacterTextSplitter` 进行分块（chunk_size=1000, chunk_overlap=200）。
  - 为每个块创建LangChain Document对象：`Document(page_content=chunk, metadata={"source": filename, "page": page_num})`。
  - 返回Document列表。

#### 5. LLM调用封装 `llm.py`
- 函数 `stream_llm_response(messages: List[Dict], model="deepseek-chat")`：
  - 使用 `httpx` 或 `aiohttp` 异步调用DeepSeek API的流式接口。
  - 逐块yield响应内容。
- 注意处理API错误和超时。

#### 6. 主应用 `app.py`
- 初始化FastAPI应用。
- 加载嵌入模型（全局单例）。
- 初始化Chroma集合（如果不存在则创建）。
- 定义API路由：
  - `POST /upload`：接收上传的PDF文件，保存临时，调用 `process_pdf` 生成文档块，调用嵌入模型生成向量，调用 `vector_store.add_documents` 入库，返回成功消息。
  - `POST /ask`：接收JSON `{"question": "..."}`，执行以下步骤：
    1. 将问题向量化。
    2. 调用 `vector_store.similarity_search` 获取Top-K文档块。
    3. 构建提示消息列表：
       ```python
       system_message = "你是一个学术文献助手，请基于以下文献片段回答问题。如果问题无法从文献中找到答案，请说明“文献中未提及”。请在每个答案末尾列出引用来源（文献名和页码）。"
       user_content = "文献片段：\n" + "\n".join([f"[{i+1}] 文献：{doc.metadata['source']}，第{doc.metadata['page']}页：{doc.page_content}" for i, doc in enumerate(docs)]) + f"\n\n问题：{question}\n答案："
       messages = [{"role": "system", "content": system_message}, {"role": "user", "content": user_content}]
       ```
    4. 调用 `stream_llm_response(messages)`，以流式响应返回（`StreamingResponse`）。
- 挂载静态文件目录 `static`。
- 启动时创建必要的目录（uploads, chroma_db）。

### 二、前端模块

#### 1. 页面结构 `static/index.html`
- 包含文件上传区域（支持拖拽和点击选择）。
- 上传进度提示（如“处理中...”）。
- 对话区域：显示历史问答列表，每个问题有独立的答案容器。
- 输入框和发送按钮。

#### 2. 样式 `static/style.css`
- 现代简洁风格，响应式设计，确保在手机和桌面均可用。
- 上传区域有虚线边框，拖拽时高亮。
- 答案区域支持Markdown样式（引用、代码块等）。

#### 3. 交互脚本 `static/script.js`
- **文件上传**：
  - 监听拖拽事件和文件选择事件，将文件通过 `FormData` 发送到 `/upload`。
  - 上传期间显示“正在解析PDF...”，成功后提示“文件已处理，可以开始提问”。
  - 错误时显示错误信息。
- **问答交互**：
  - 监听发送按钮和回车，获取输入框内容。
  - 将问题添加到对话区域（用户消息样式）。
  - 清空输入框，显示“正在思考...”占位。
  - 使用 `fetch` 发送POST请求到 `/ask`，设置 `responseType: 'stream'`，并通过 `TextDecoder` 逐步解析响应数据。
  - 每收到一个数据块，将其附加到当前答案容器中（使用 `marked.parse` 实时渲染Markdown）。
  - 流结束后，移除“正在思考...”占位。
- **引用点击**：将答案中形如 `[1]` 的标记转换为可点击链接，点击时弹出模态框显示对应文献片段（可选简单实现，如alert显示原文；或可扩展为模态框）。

### 三、项目结构
academic-rag/
├── app.py
├── config.py
├── embedding.py
├── vector_store.py
├── pdf_processor.py
├── llm.py
├── requirements.txt
├── .env.example
├── static/
│ ├── index.html
│ ├── style.css
│ ├── script.js
│ └── upload-icon.svg（可选）
├── uploads/ # 自动创建
└── chroma_db/ # 自动创建

### 四、依赖清单 `requirements.txt`
fastapi
uvicorn[standard]
python-multipart
aiofiles
chromadb
langchain
sentence-transformers
PyMuPDF
python-dotenv
httpx
marked # 如果需要在前端使用marked库，需通过CDN引入，不在requirements中

### 五、环境与运行
1. 克隆项目，创建虚拟环境，安装依赖。
2. 复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY`。
3. 运行 `python app.py`，访问 `http://localhost:8000`。

### 六、注意事项
- 嵌入模型首次运行时会自动下载，请确保网络通畅。
- 上传的PDF文件需为可复制文本，扫描版可能无法提取内容。
- DeepSeek API调用需要密钥，且流式接口需正确处理。
- 前端流式输出使用 `fetch` 和 `TextDecoder`，需注意浏览器兼容性。

---

## 开发目标
生成完整可运行的代码，每个文件包含必要注释，确保功能正确，用户可顺利上传PDF并进行问答。代码需简洁、模块化，便于理解和二次开发。