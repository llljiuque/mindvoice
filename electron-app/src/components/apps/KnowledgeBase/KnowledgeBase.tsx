import React, { useState, useEffect, useRef } from 'react';
import { AppLayout } from '../../shared/AppLayout';
import './KnowledgeBase.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8765';

interface KnowledgeFile {
  file_id: string;
  filename: string;
  chunks: number;
  metadata?: Record<string, any>;
}

export const KnowledgeBase: React.FC = () => {
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<KnowledgeFile | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 加载文件列表
  const loadFiles = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/knowledge/files`);
      const data = await response.json();
      if (data.success) {
        setFiles(data.files);
      }
    } catch (error) {
      console.error('加载文件列表失败:', error);
      setMessage({ text: '加载文件列表失败', type: 'error' });
      setTimeout(() => setMessage(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
  }, []);

  // 上传文件
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !['md', 'txt'].includes(ext)) {
      setMessage({ text: '仅支持 .md 和 .txt 文件', type: 'error' });
      setTimeout(() => setMessage(null), 3000);
      return;
    }

    try {
      const content = await file.text();
      
      const response = await fetch(`${API_BASE_URL}/api/knowledge/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          content: content
        })
      });

      const data = await response.json();
      if (data.success) {
        setMessage({ text: '上传成功！', type: 'success' });
        setTimeout(() => setMessage(null), 3000);
        loadFiles();
      } else {
        setMessage({ text: '上传失败', type: 'error' });
        setTimeout(() => setMessage(null), 3000);
      }
    } catch (error) {
      console.error('上传文件失败:', error);
      setMessage({ text: '上传文件失败', type: 'error' });
      setTimeout(() => setMessage(null), 3000);
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // 删除文件
  const handleDeleteFile = async (fileId: string) => {
    if (!confirm('确定要删除这个文件吗？')) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/knowledge/files/${fileId}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      if (data.success) {
        setMessage({ text: '删除成功', type: 'success' });
        setTimeout(() => setMessage(null), 3000);
        loadFiles();
        if (selectedFile?.file_id === fileId) {
          setSelectedFile(null);
          setFileContent('');
        }
      }
    } catch (error) {
      console.error('删除文件失败:', error);
      setMessage({ text: '删除文件失败', type: 'error' });
      setTimeout(() => setMessage(null), 3000);
    }
  };

  // 查看文件内容
  const handleViewFile = async (file: KnowledgeFile) => {
    setSelectedFile(file);
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/knowledge/files/${file.file_id}/content`);
      const data = await response.json();
      if (data.success) {
        setFileContent(data.content);
      }
    } catch (error) {
      console.error('获取文件内容失败:', error);
      setFileContent('加载失败');
    } finally {
      setLoading(false);
    }
  };

  // 过滤文件
  const filteredFiles = files.filter(file =>
    file.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <AppLayout
      title="知识库"
      subtitle="文件管理 · 智能检索 · 语义搜索"
      icon="📚"
    >
      <div className="knowledge-view">
        <div className="knowledge-container">
          <div className="knowledge-content">
          {/* 消息提示 */}
          {message && (
            <div className={`knowledge-message knowledge-message-${message.type}`}>
              {message.type === 'success' ? '✓' : '✕'} {message.text}
            </div>
          )}

          {/* 上传区域 */}
          <div className="knowledge-section">
            <div className="section-header">
              <h2 className="section-title">上传文件</h2>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="knowledge-btn knowledge-btn-primary"
                disabled={loading}
              >
                <span>➕</span>
                <span>上传文件</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".md,.txt"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
              />
            </div>
            <p className="section-description">
              支持 Markdown (.md) 和文本 (.txt) 文件，文件会被自动分块和向量化，用于智能检索
            </p>
          </div>

          {/* 文件列表 */}
          <div className="knowledge-section">
            <h2 className="section-title">文件列表</h2>
            
            {/* 搜索框 */}
            <div className="knowledge-search">
              <input
                type="text"
                placeholder="🔍 搜索文件名..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="knowledge-search-input"
              />
            </div>

            {/* 文件列表内容 */}
            {loading && files.length === 0 ? (
              <div className="knowledge-loading">
                <div className="loading-spinner"></div>
                <span>加载中...</span>
              </div>
            ) : filteredFiles.length === 0 ? (
              <div className="knowledge-empty">
                <p>{searchQuery ? '未找到匹配的文件' : '暂无文件，点击上传按钮添加'}</p>
              </div>
            ) : (
              <div className="knowledge-file-list">
                {filteredFiles.map(file => (
                  <div
                    key={file.file_id}
                    className={`knowledge-file-item ${selectedFile?.file_id === file.file_id ? 'active' : ''}`}
                    onClick={() => handleViewFile(file)}
                  >
                    <div className="file-icon">
                      {file.filename.endsWith('.md') ? '📝' : '📄'}
                    </div>
                    <div className="file-info">
                      <div className="file-name">{file.filename}</div>
                      <div className="file-meta">{file.chunks} 个文本块</div>
                    </div>
                    <button
                      className="delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteFile(file.file_id);
                      }}
                      title="删除"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 文件预览 */}
          {selectedFile && (
            <div className="knowledge-section">
              <div className="section-header">
                <h2 className="section-title">文件预览</h2>
                <button
                  onClick={() => {
                    setSelectedFile(null);
                    setFileContent('');
                  }}
                  className="knowledge-btn knowledge-btn-secondary"
                >
                  关闭预览
                </button>
              </div>
              
              <div className="file-preview">
                <div className="file-preview-header">
                  <div className="file-preview-name">
                    {selectedFile.filename.endsWith('.md') ? '📝' : '📄'} {selectedFile.filename}
                  </div>
                  <div className="file-preview-meta">
                    {selectedFile.chunks} 个文本块
                  </div>
                </div>
                <div className="file-preview-content">
                  {loading ? (
                    <div className="knowledge-loading">
                      <div className="loading-spinner"></div>
                      <span>加载中...</span>
                    </div>
                  ) : (
                    <pre className="file-preview-text">{fileContent}</pre>
                  )}
                </div>
              </div>
            </div>
          )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

