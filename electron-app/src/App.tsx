import { useState, useEffect, useRef } from 'react';
import './App.css';

// API配置 - 可以从Electron主进程获取
const API_BASE_URL = 'http://127.0.0.1:8765';
const WS_URL = 'ws://127.0.0.1:8765/ws';

type RecordingState = 'idle' | 'recording' | 'paused' | 'processing';

interface Record {
  id: string;
  text: string;
  metadata: any;
  created_at: string;
}

function App() {
  const [state, setState] = useState<RecordingState>('idle');
  const [text, setText] = useState(''); // 显示缓冲区：显示给用户的文本
  const [error, setError] = useState<string | null>(null);
  const [apiConnected, setApiConnected] = useState(false);
  const [activeTab, setActiveTab] = useState<'recording' | 'history'>('recording');
  const [records, setRecords] = useState<Record[]>([]);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [isUserEditing, setIsUserEditing] = useState(false);
  
  // 双缓冲机制
  const asrBufferRef = useRef<string>(''); // ASR缓冲区：存储ASR推送的原始文本
  const userEditBufferRef = useRef<string>(''); // 用户编辑缓冲区：存储用户编辑的文本
  const lastMergedAsrRef = useRef<string>(''); // 记录上次合并时的ASR文本，用于检测新增内容
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isEditingRef = useRef(false); // 使用ref实时跟踪编辑状态，避免状态更新延迟
  const cursorPositionRef = useRef<number | null>(null); // 保存光标位置
  const editingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const syncTimeoutRef = useRef<NodeJS.Timeout | null>(null); // 同步用户编辑到后端的定时器
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 检查API服务器连接
  const checkApiConnection = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/status`);
      if (response.ok) {
        setApiConnected(true);
        setError(null);
        return true;
      }
    } catch (e) {
      setApiConnected(false);
      setError('无法连接到API服务器，请确保后端服务正在运行');
    }
    return false;
  };

  // 连接WebSocket
  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('WebSocket连接已建立');
        setError(null);
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('收到WebSocket消息:', data);

          switch (data.type) {
            case 'initial_state':
              setState(data.state);
              const initialText = data.text || '';
              setText(initialText);
              asrBufferRef.current = initialText;
              userEditBufferRef.current = initialText;
              lastMergedAsrRef.current = initialText;
              break;
            case 'text_update':
              handleAsrTextUpdate(data.text);
              break;
            case 'state_change':
              setState(data.state);
              break;
            case 'error':
              setError(`${data.error_type}: ${data.message}`);
              break;
          }
        } catch (e) {
          console.error('解析WebSocket消息失败:', e);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
        if (!apiConnected) {
          setError('WebSocket连接错误，请确保API服务器正在运行');
        }
      };

      ws.onclose = () => {
        console.log('WebSocket连接已关闭');
        wsRef.current = null;
        
        // 如果API已连接，尝试重连
        if (apiConnected && !reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            connectWebSocket();
          }, 3000);
        }
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('WebSocket连接失败:', e);
      if (!apiConnected) {
        setError('无法连接到API服务器');
      }
    }
  };

  useEffect(() => {
    // 初始检查API连接
    checkApiConnection().then((connected) => {
      if (connected) {
        connectWebSocket();
      }
    });

    // 定期检查API连接
    const interval = setInterval(() => {
      checkApiConnection().then((connected) => {
        if (connected && !wsRef.current) {
          connectWebSocket();
        }
      });
    }, 5000);

    return () => {
      clearInterval(interval);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (editingTimeoutRef.current) {
        clearTimeout(editingTimeoutRef.current);
      }
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/recording/start`, {
        method: 'POST',
      });
      const data = await response.json();
      if (!data.success) {
        setError(data.message);
      } else {
        setError(null);
      }
    } catch (e) {
      setError(`启动录音失败: ${e}`);
    }
  };

  const pauseRecording = async () => {
    try {
      // 暂停前，如果有用户编辑，先同步
      if (isEditingRef.current || userEditBufferRef.current !== asrBufferRef.current) {
        // 停止编辑状态
        if (isEditingRef.current) {
          isEditingRef.current = false;
          setIsUserEditing(false);
          if (editingTimeoutRef.current) {
            clearTimeout(editingTimeoutRef.current);
            editingTimeoutRef.current = null;
          }
          mergeAsrUpdates();
        }
        // 同步用户编辑版本
        await syncUserEditToBackend(userEditBufferRef.current);
      }
      
      const response = await fetch(`${API_BASE_URL}/api/recording/pause`, {
        method: 'POST',
      });
      const data = await response.json();
      if (!data.success) {
        setError(data.message);
      }
    } catch (e) {
      setError(`暂停录音失败: ${e}`);
    }
  };

  const resumeRecording = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/recording/resume`, {
        method: 'POST',
      });
      const data = await response.json();
      if (!data.success) {
        setError(data.message);
      }
    } catch (e) {
      setError(`恢复录音失败: ${e}`);
    }
  };

  const stopRecording = async () => {
    try {
      // 停止录音前，先保存用户编辑的版本（如果有）
      if (isEditingRef.current || userEditBufferRef.current !== asrBufferRef.current) {
        // 用户正在编辑或编辑过，先同步用户编辑版本
        await syncUserEditToBackend(userEditBufferRef.current);
        // 等待同步完成
        await new Promise(resolve => setTimeout(resolve, 300));
      }
      
      // 停止编辑状态，执行最终合并
      if (isEditingRef.current) {
        isEditingRef.current = false;
        setIsUserEditing(false);
        mergeAsrUpdates();
        // 等待合并完成
        await new Promise(resolve => setTimeout(resolve, 300));
      }
      
      const response = await fetch(`${API_BASE_URL}/api/recording/stop`, {
        method: 'POST',
      });
      const data = await response.json();
      
      // 停止录音后，使用用户编辑版本（如果有），否则使用ASR最终版本
      const finalText = userEditBufferRef.current || data.final_text || '';
      if (finalText) {
        setText(finalText);
        userEditBufferRef.current = finalText;
        asrBufferRef.current = data.final_text || finalText;
      }
      
      if (!data.success) {
        setError(data.message);
      }
    } catch (e) {
      setError(`停止录音失败: ${e}`);
    }
  };

  const copyText = async () => {
    if (!text) {
      setError('没有可复制的文本');
      return;
    }

    try {
      await navigator.clipboard.writeText(text);
      // 可以添加toast提示
      console.log('文本已复制到剪贴板');
    } catch (e) {
      setError(`复制失败: ${e}`);
    }
  };

  const loadRecords = async () => {
    if (!apiConnected) return;
    
    setLoadingRecords(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/records?limit=100&offset=0`);
      const data = await response.json();
      if (data.success) {
        setRecords(data.records);
      } else {
        setError('加载历史记录失败');
      }
    } catch (e) {
      setError(`加载历史记录失败: ${e}`);
    } finally {
      setLoadingRecords(false);
    }
  };

  const deleteRecord = async (recordId: string) => {
    if (!apiConnected) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/records/${recordId}`, {
        method: 'DELETE',
      });
      const data = await response.json();
      if (data.success) {
        // 重新加载记录列表
        await loadRecords();
      } else {
        setError('删除记录失败');
      }
    } catch (e) {
      setError(`删除记录失败: ${e}`);
    }
  };

  const loadRecord = async (recordId: string) => {
    if (!apiConnected) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/records/${recordId}`);
      const data = await response.json();
      if (data.text) {
        setText(data.text);
        setActiveTab('recording');
      }
    } catch (e) {
      setError(`加载记录失败: ${e}`);
    }
  };

  useEffect(() => {
    if (activeTab === 'history' && apiConnected) {
      loadRecords();
    }
  }, [activeTab, apiConnected]);

  // ASR更新处理 - 双缓冲机制
  const handleAsrTextUpdate = (asrText: string) => {
    // 1. 更新ASR缓冲区（始终更新，后端会自动保存）
    asrBufferRef.current = asrText;

    // 2. 如果用户没有在编辑，直接同步到显示和用户编辑缓冲区
    if (!isEditingRef.current) {
      setText(asrText);
      userEditBufferRef.current = asrText;
      lastMergedAsrRef.current = asrText;
    } else {
      // 3. 用户正在编辑时，ASR更新不干扰用户编辑
      // ASR内容已经在后端保存了，前端保持用户编辑的内容和光标位置不变
      // 但记录ASR的新内容，等待用户停止编辑时合并
    }
  };


  // 处理用户输入
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    // 实时更新ref，确保ASR更新时能立即检测到编辑状态
    isEditingRef.current = true;
    setIsUserEditing(true);
    
    // 保存光标位置
    cursorPositionRef.current = e.target.selectionStart;
    
    const userText = e.target.value;
    
    // 更新显示缓冲区和用户编辑缓冲区
    setText(userText);
    userEditBufferRef.current = userText;
    
    // 清除之前的定时器
    if (editingTimeoutRef.current) {
      clearTimeout(editingTimeoutRef.current);
    }
    if (syncTimeoutRef.current) {
      clearTimeout(syncTimeoutRef.current);
    }
    
    // 设置新的定时器：用户停止输入2秒后，标记为停止编辑并合并ASR新内容
    editingTimeoutRef.current = setTimeout(() => {
      isEditingRef.current = false;
      setIsUserEditing(false);
      cursorPositionRef.current = null;
      editingTimeoutRef.current = null;
      
      // 用户停止编辑后，合并ASR新内容
      mergeAsrUpdates();
    }, 2000);
    
    // 延迟同步用户编辑到后端（防抖）
    syncTimeoutRef.current = setTimeout(() => {
      syncUserEditToBackend(userText);
    }, 1000);
  };
  
  // 合并ASR更新到用户编辑缓冲区
  const mergeAsrUpdates = () => {
    const currentAsr = asrBufferRef.current;
    const lastMerged = lastMergedAsrRef.current;
    const userEdit = userEditBufferRef.current;
    
    // 如果ASR和用户编辑相同，无需合并
    if (currentAsr === userEdit) {
      lastMergedAsrRef.current = currentAsr;
      return;
    }
    
    // 检测ASR是否有新内容（追加）
    if (lastMerged && currentAsr.startsWith(lastMerged)) {
      const newAsrContent = currentAsr.slice(lastMerged.length);
      if (newAsrContent.length > 0) {
        // ASR在末尾追加了新内容，追加到用户编辑文本的末尾
        const mergedText = userEdit + newAsrContent;
        setText(mergedText);
        userEditBufferRef.current = mergedText;
        lastMergedAsrRef.current = currentAsr;
        
        // 同步合并后的文本到后端
        syncUserEditToBackend(mergedText);
        return;
      }
    }
    
    // ASR内容发生了其他变化（可能是修正），但用户已经编辑了
    // 策略：保持用户编辑版本，因为用户已经做了修改
    // 但更新lastMergedAsrRef，避免重复检测
    if (currentAsr !== lastMerged) {
      console.log('[合并] ASR内容变化，但保持用户编辑版本');
      // 不更新lastMergedAsrRef，因为用户编辑版本可能与ASR不同
      // 下次合并时，如果ASR追加了新内容，仍然可以合并
    }
  };
  
  // 同步用户编辑到后端（带防抖和去重）
  const syncUserEditToBackend = async (userText: string) => {
    if (!apiConnected || (state !== 'recording' && state !== 'paused')) {
      return;
    }
    
    try {
      // 调用API同步用户编辑的文本
      const response = await fetch(`${API_BASE_URL}/api/recording/sync-edit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: userText }),
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          console.log('[同步] 用户编辑已同步到后端');
        }
      }
    } catch (e) {
      console.error('[同步] 同步用户编辑失败:', e);
    }
  };

  // 处理用户停止编辑（失去焦点）
  const handleTextBlur = () => {
    // 保存当前光标位置和用户编辑内容
    if (textareaRef.current) {
      cursorPositionRef.current = textareaRef.current.selectionStart;
      const userText = textareaRef.current.value;
      userEditBufferRef.current = userText;
    }
    
    // 延迟标记为停止编辑，给用户时间继续输入
    if (editingTimeoutRef.current) {
      clearTimeout(editingTimeoutRef.current);
    }
    editingTimeoutRef.current = setTimeout(() => {
      isEditingRef.current = false;
      setIsUserEditing(false);
      cursorPositionRef.current = null;
      editingTimeoutRef.current = null;
      
      // 用户停止编辑后，合并ASR新内容
      mergeAsrUpdates();
    }, 500);
  };

  // 处理用户点击/选择文本（保存光标位置）
  const handleTextSelect = () => {
    if (textareaRef.current) {
      isEditingRef.current = true;
      setIsUserEditing(true);
      cursorPositionRef.current = textareaRef.current.selectionStart;
      
      // 清除之前的定时器
      if (editingTimeoutRef.current) {
        clearTimeout(editingTimeoutRef.current);
      }
      
      // 设置新的定时器
      editingTimeoutRef.current = setTimeout(() => {
        isEditingRef.current = false;
        setIsUserEditing(false);
        cursorPositionRef.current = null;
        editingTimeoutRef.current = null;
      }, 2000);
    }
  };

  // 清理定时器
  useEffect(() => {
    return () => {
      if (editingTimeoutRef.current) {
        clearTimeout(editingTimeoutRef.current);
      }
    };
  }, []);

  const getStatusText = () => {
    if (!apiConnected) {
      return '未连接';
    }
    switch (state) {
      case 'recording':
        return '录音中...';
      case 'paused':
        return '已暂停';
      case 'processing':
        return '处理中...';
      default:
        return '就绪';
    }
  };

  const getStatusColor = () => {
    if (!apiConnected) {
      return '#f44336';
    }
    switch (state) {
      case 'recording':
        return '#4CAF50';
      case 'paused':
        return '#ff9800';
      case 'processing':
        return '#9c27b0';
      default:
        return '#757575';
    }
  };

  return (
    <div className="app">
      <div className="header">
        <h1>MindVoice</h1>
        <div className="status" style={{ backgroundColor: getStatusColor() }}>
          {getStatusText()}
        </div>
      </div>

      <div className="tabs">
        <button
          className={activeTab === 'recording' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('recording')}
        >
          录音
        </button>
        <button
          className={activeTab === 'history' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('history')}
        >
          历史记录
        </button>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {activeTab === 'recording' ? (
        <>
          <div className="text-display">
            <textarea
              ref={textareaRef}
              value={text}
              onChange={handleTextChange}
              onBlur={handleTextBlur}
              onSelect={handleTextSelect}
              onKeyDown={() => {
                // 用户按键时，确保标记为编辑状态
                if (!isEditingRef.current) {
                  isEditingRef.current = true;
                  setIsUserEditing(true);
                }
              }}
              placeholder={state === 'recording' ? '正在识别中...' : state === 'paused' ? '已暂停，点击恢复继续识别' : '点击"开始"按钮开始语音识别'}
              className="text-area"
              style={{ 
                cursor: isUserEditing ? 'text' : 'default',
                backgroundColor: isUserEditing ? '#fffef7' : '#ffffff'
              }}
            />
            {isUserEditing && (
              <div className="editing-indicator">
                <span style={{ fontSize: '12px', color: '#ff9800' }}>✏️ 编辑中 - ASR持续记录中</span>
              </div>
            )}
          </div>

          <div className="controls">
            <button
              onClick={startRecording}
              disabled={!apiConnected || state === 'recording' || state === 'processing'}
              className="btn btn-start"
            >
              开始
            </button>

            {state === 'recording' ? (
              <button
                onClick={pauseRecording}
                disabled={!apiConnected}
                className="btn btn-pause"
              >
                暂停
              </button>
            ) : state === 'paused' ? (
              <button
                onClick={resumeRecording}
                disabled={!apiConnected}
                className="btn btn-resume"
              >
                恢复
              </button>
            ) : null}

            <button
              onClick={stopRecording}
              disabled={!apiConnected || state === 'idle' || state === 'processing'}
              className="btn btn-stop"
            >
              停止
            </button>

            <button
              onClick={copyText}
              disabled={!text}
              className="btn btn-copy"
            >
              复制
            </button>
          </div>
        </>
      ) : (
        <div className="history-panel">
          {loadingRecords ? (
            <div className="loading">加载中...</div>
          ) : records.length === 0 ? (
            <div className="empty-state">
              <div style={{ fontSize: '48px', marginBottom: '12px', opacity: 0.3 }}>📝</div>
              <div>暂无历史记录</div>
              <div style={{ fontSize: '12px', marginTop: '8px', color: '#bbb' }}>开始录音后，记录将自动保存</div>
            </div>
          ) : (
            <div className="records-list">
              {records.map((record) => (
                <div key={record.id} className="record-item">
                  <div className="record-header">
                    <span className="record-date">
                      {new Date(record.created_at).toLocaleString('zh-CN')}
                    </span>
                    <div className="record-actions">
                      <button
                        className="btn-small btn-load"
                        onClick={() => loadRecord(record.id)}
                      >
                        查看
                      </button>
                      <button
                        className="btn-small btn-delete"
                        onClick={() => deleteRecord(record.id)}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                  <div className="record-text">
                    {record.text.length > 100
                      ? `${record.text.substring(0, 100)}...`
                      : record.text || '(空)'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;

