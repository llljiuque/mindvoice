/**
 * VoiceChat 应用的自动保存适配器
 */

import { AppAdapter, SaveData } from '../AutoSaveService';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  isStreaming?: boolean;  // 正在流式输出
}

export interface VoiceChatData {
  messages: Message[];
  conversationContext?: any;
}

/**
 * VoiceChat 适配器
 */
export class VoiceChatAdapter implements AppAdapter {
  private getMessagesFn: () => Message[];
  private getContextFn: () => any;
  
  constructor(
    getMessages: () => Message[],
    getContext: () => any
  ) {
    this.getMessagesFn = getMessages;
    this.getContextFn = getContext;
  }
  
  /**
   * 获取所有数据
   */
  getAllData(): VoiceChatData {
    return {
      messages: this.getMessagesFn(),
      conversationContext: this.getContextFn(),
    };
  }
  
  /**
   * 判断 message 是否处于临时状态
   */
  isVolatile(item: Message): boolean {
    // 正在流式输出的消息
    if (item.isStreaming) {
      return true;
    }
    
    return false;
  }
  
  /**
   * 获取稳定的数据
   */
  getStableData(): VoiceChatData {
    const allData = this.getAllData();
    
    return {
      messages: allData.messages.filter(msg => !this.isVolatile(msg)),
      conversationContext: allData.conversationContext,
    };
  }
  
  /**
   * 转换为保存格式
   */
  toSaveData(stableData: VoiceChatData): SaveData {
    const { messages, conversationContext } = stableData;
    
    // 将 messages 转换为文本格式
    const textContent = messages
      .map(msg => {
        const rolePrefix = msg.role === 'user' ? '用户: ' : 
                          msg.role === 'assistant' ? 'AI: ' : 
                          '系统: ';
        return `${rolePrefix}${msg.content}`;
      })
      .join('\n\n');
    
    return {
      text: textContent,
      app_type: 'voice-chat',
      metadata: {
        messages,
        conversationContext,
        message_count: messages.length,
      },
    };
  }
  
  /**
   * 检查是否有内容
   */
  hasContent(data: VoiceChatData): boolean {
    const { messages } = data;
    
    // 至少有一条有效消息
    return messages.length > 0 && messages.some(msg => msg.content.trim());
  }
}

