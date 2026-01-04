/**
 * VoiceZen（禅应用）的自动保存适配器
 */

import { AppAdapter, SaveData } from '../AutoSaveService';

export interface ZenEntry {
  id: string;
  content: string;
  timestamp: number;
  isWriting?: boolean;  // 正在书写
}

export interface VoiceZenData {
  entries: ZenEntry[];
  zenState?: {
    mode?: string;  // 禅模式
    theme?: string; // 主题
  };
}

/**
 * VoiceZen 适配器
 */
export class VoiceZenAdapter implements AppAdapter {
  private getEntriesFn: () => ZenEntry[];
  private getStateFn: () => any;
  
  constructor(
    getEntries: () => ZenEntry[],
    getState: () => any
  ) {
    this.getEntriesFn = getEntries;
    this.getStateFn = getState;
  }
  
  /**
   * 获取所有数据
   */
  getAllData(): VoiceZenData {
    return {
      entries: this.getEntriesFn(),
      zenState: this.getStateFn(),
    };
  }
  
  /**
   * 判断 entry 是否处于临时状态
   */
  isVolatile(item: ZenEntry): boolean {
    // 正在书写的条目
    if (item.isWriting) {
      return true;
    }
    
    return false;
  }
  
  /**
   * 获取稳定的数据
   */
  getStableData(): VoiceZenData {
    const allData = this.getAllData();
    
    return {
      entries: allData.entries.filter(entry => !this.isVolatile(entry)),
      zenState: allData.zenState,
    };
  }
  
  /**
   * 转换为保存格式
   */
  toSaveData(stableData: VoiceZenData): SaveData {
    const { entries, zenState } = stableData;
    
    // 将 entries 转换为文本格式
    const textContent = entries
      .map(entry => entry.content)
      .filter(content => content.trim())
      .join('\n\n---\n\n');
    
    return {
      text: textContent,
      app_type: 'voice-zen',
      metadata: {
        entries,
        zenState,
        entry_count: entries.length,
      },
    };
  }
  
  /**
   * 检查是否有内容
   */
  hasContent(data: VoiceZenData): boolean {
    const { entries } = data;
    
    // 至少有一条有效条目
    return entries.length > 0 && entries.some(entry => entry.content.trim());
  }
}

