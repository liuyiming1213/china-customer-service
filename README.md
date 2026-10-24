# 日本游戏客服智能化项目

这是一个前后端分离的客服辅助系统 MVP：

- 后端：FastAPI；
- 前端：Vue 3 + Vite；
- 长期知识：ChromaDB；
- Embedding：Qwen3-Embedding-0.6B；
- Reranker：BGE-Reranker；
- 生成和判断：DashScope OpenAI-compatible API 的 qwen3.7-flash；
- 本地摘要和状态：SQLite 开发实现，后续可切换 PostgreSQL。

## 启动前准备

1. 使用 Python 3.12 创建虚拟环境。
2. 安装 `requirements.txt`。
3. 复制 `.env.example` 为 `.env`，设置 `DASHSCOPE_API_KEY`。
4. 运行模型下载脚本。
5. 运行知识库导入脚本。

后端启动地址：`http://localhost:8000`

前端启动地址：`http://localhost:5173`

## 关键命令

```text
python -m uvicorn app.main:app --app-dir backend --reload
python backend/scripts/download_models.py
python backend/scripts/ingest_knowledge.py
```

首次在资源受限的本机验证时，可使用 `INGEST_MAX_THREADS=64` 只导入一批案例；完整导入时移除该变量。生产环境应在 GPU 或专用模型服务上完成全量索引。

如果本机无法承载 BGE-Reranker，可将 `ENABLE_RERANKER=false` 作为临时降级配置；系统会使用 Chroma 的向量召回顺序，并保留 BGE-Reranker 的生产配置入口。

前端命令在 `frontend` 目录执行：

```text
npm install
npm run dev
```

## 当前边界

当前版本是客服辅助 MVP，回复默认需要人工审核。系统不会自动执行退款、补偿、封禁、账号恢复或其他后台操作。

如果本地没有 CUDA 或 CPU 内存不足，可以临时将 `EMBEDDING_MODEL` 设置为 `intfloat/multilingual-e5-small` 完成首次索引；生产环境建议恢复为 Qwen3-Embedding-0.6B，并在 GPU 或专用模型服务上重建 Chroma 索引。
