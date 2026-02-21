import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from config import UPLOAD_DIR, VECTOR_DB_DIR, TOP_K
from embedding import get_embedding_model
from vector_store import get_vector_store
from pdf_processor import process_pdf
from llm import stream_llm_response

app = FastAPI(title="学术论文问答系统")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VECTOR_DB_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

embedding_model = get_embedding_model()
vector_store = get_vector_store()

class QuestionRequest(BaseModel):
    question: str

class FileInfo(BaseModel):
    filename: str
    chunks: int
    upload_time: str

@app.get("/files")
async def list_files():
    try:
        files = []
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                if filename.endswith('.pdf'):
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    upload_time = os.path.getmtime(file_path)
                    from datetime import datetime
                    upload_time_str = datetime.fromtimestamp(upload_time).strftime('%Y-%m-%d %H:%M')
                    files.append(FileInfo(filename=filename, chunks=0, upload_time=upload_time_str))
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@app.delete("/files/{filename}")
async def delete_file(filename: str):
    try:
        if not filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="仅支持删除PDF文件")
        
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        os.remove(file_path)
        vector_store.remove_documents_by_source(filename)
        
        return {"message": f"文件 {filename} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="仅支持PDF文件")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        documents = process_pdf(file_path, file.filename)
        if not documents:
            raise HTTPException(status_code=400, detail="无法从PDF中提取文本内容")
        
        embeddings = embedding_model.embed_documents([doc.page_content for doc in documents])
        vector_store.add_documents(documents, embeddings)
        
        return {"message": f"文件 {file.filename} 已成功处理，共 {len(documents)} 个文档块", "filename": file.filename, "chunks": len(documents)}
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"处理文件时出错: {str(e)}")

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    query_embedding = embedding_model.embed_text(question)
    docs = vector_store.similarity_search(query_embedding, k=TOP_K)
    
    if not docs:
        async def empty_response():
            yield "文献中未找到相关内容，请上传相关论文后重试。"
        return StreamingResponse(empty_response(), media_type="text/plain")
    
    system_message = "你是一个学术文献助手，请基于以下文献片段回答问题。如果问题无法从文献中找到答案，请说明\"文献中未提及\"。请在每个答案末尾列出引用来源（文献名和页码）。"
    
    user_content = "文献片段：\n" + "\n".join(
        [f"[{i+1}] 文献：{doc.metadata['source']}，第{doc.metadata['page']}页：{doc.page_content}" 
         for i, doc in enumerate(docs)]
    ) + f"\n\n问题：{question}\n答案："
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_content}
    ]
    
    return StreamingResponse(stream_llm_response(messages), media_type="text/plain")

@app.delete("/clear")
async def clear_all():
    try:
        vector_store.clear()
        
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        return {"message": "已清除所有上传的PDF文件和向量数据库"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除失败: {str(e)}")

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
