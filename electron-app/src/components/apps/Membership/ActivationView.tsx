/**
 * 激活码激活界面
 */

import React, { useState } from 'react';
import './ActivationView.css';

const API_BASE_URL = 'http://127.0.0.1:8765';

interface ActivationViewProps {
  deviceId: string;
}

export const ActivationView: React.FC<ActivationViewProps> = ({ deviceId }) => {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [userId, setUserId] = useState<string | null>(null);

  // 获取 user_id
  React.useEffect(() => {
    const fetchUserId = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/user/profile/${deviceId}`);
        const data = await response.json();
        if (data.success && data.data) {
          setUserId(data.data.user_id);
        }
      } catch (err) {
        console.error('[激活] 获取用户ID失败:', err);
      }
    };
    fetchUserId();
  }, [deviceId]);

  const handleActivate = async () => {
    if (!code.trim()) {
      setMessage({ type: 'error', text: '请输入激活码' });
      return;
    }

    if (!userId) {
      setMessage({ type: 'error', text: '用户信息加载中，请稍候' });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/membership/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          activation_code: code.trim(),
        }),
      });

      const data = await response.json();

      if (data.success) {
        setMessage({ type: 'success', text: data.message || '激活成功！' });
        setCode('');
      } else {
        setMessage({ type: 'error', text: data.error || '激活失败' });
      }
    } catch (err) {
      console.error('[激活] 失败:', err);
      setMessage({ type: 'error', text: '网络错误，请稍后重试' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="activation-view">
      <div className="activation-card">
        <div className="activation-header">
          <h2>激活会员</h2>
          <p className="subtitle">输入激活码升级您的会员等级</p>
        </div>

        <div className="activation-form">
          <div className="input-group">
            <label htmlFor="activation-code">激活码</label>
            <input
              id="activation-code"
              type="text"
              className="activation-input"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="例如：VIP-1-XXXX-XXXX"
              disabled={loading}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && code.trim() && !loading) {
                  handleActivate();
                }
              }}
            />
            <p className="input-hint">激活码格式：TIER-MONTHS-XXXX-XXXX</p>
          </div>

          {message && (
            <div className={`message ${message.type === 'error' ? 'error-message' : 'success-message'}`}>
              {message.text}
            </div>
          )}

          <div className="button-group">
            <button
              className="activate-btn"
              onClick={handleActivate}
              disabled={loading || !code.trim()}
            >
              {loading ? '激活中...' : '立即激活'}
            </button>
          </div>
        </div>

        <div className="help-section">
          <h4>如何获取激活码？</h4>
          <ul>
            <li>联系客服购买激活码</li>
            <li>参与活动获取免费激活码</li>
            <li>推荐好友获得奖励激活码</li>
          </ul>
          <div className="contact-info">
            <strong>联系方式:</strong>
            <div>邮箱: manwjh@126.com</div>
            <div>微信: 13510090675</div>
          </div>
        </div>
      </div>
    </div>
  );
};
