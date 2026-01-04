/**
 * VoiceNote 应用的自动保存适配器
 */

import { AppAdapter, SaveData } from '../AutoSaveService';

export interface Block {
  id: string;
  type: string;
  content: string;
  isAsrWriting?: boolean;
  isBufferBlock?: boolean;
  isSummary?: boolean;
  noteInfo?: any;
  imageUrl?: string;
  [key: string]: any;
}

export interface VoiceNoteData {
  blocks: Block[];
  noteInfo?: any;
}

/**
 * VoiceNote 适配器
 */
export class VoiceNoteAdapter implements AppAdapter {
  private getBlocksFn: () => Block[];
  private getNoteInfoFn: () => any;
  private editingBlockId: string | null = null;
  
  constructor(
    getBlocks: () => Block[],
    getNoteInfo: () => any
  ) {
    this.getBlocksFn = getBlocks;
    this.getNoteInfoFn = getNoteInfo;
  }
  
  /**
   * 设置当前编辑的 block ID
   */
  setEditingBlockId(blockId: string | null) {
    this.editingBlockId = blockId;
  }
  
  /**
   * 获取所有数据
   */
  getAllData(): VoiceNoteData {
    return {
      blocks: this.getBlocksFn(),
      noteInfo: this.getNoteInfoFn(),
    };
  }
  
  /**
   * 判断 block 是否处于临时状态
   */
  isVolatile(item: Block): boolean {
    // ASR 正在写入
    if (item.isAsrWriting) {
      return true;
    }
    
    // 用户正在编辑
    if (this.editingBlockId === item.id) {
      return true;
    }
    
    return false;
  }
  
  /**
   * 获取稳定的数据
   */
  getStableData(): VoiceNoteData {
    const allData = this.getAllData();
    
    console.log('[VoiceNoteAdapter] 🔍 getStableData - allData:', {
      totalBlocks: allData.blocks.length,
      noteInfo: allData.noteInfo,
    });
    
    const stableBlocks = allData.blocks.filter(block => !this.isVolatile(block));
    
    console.log('[VoiceNoteAdapter] 🔍 getStableData - stableBlocks:', {
      stableBlocksCount: stableBlocks.length,
      totalBlocks: allData.blocks.length,
    });
    
    return {
      blocks: stableBlocks,
      noteInfo: allData.noteInfo,
    };
  }
  
  /**
   * 转换为保存格式
   */
  toSaveData(stableData: VoiceNoteData): SaveData {
    const { blocks, noteInfo } = stableData;
    
    console.log('[VoiceNoteAdapter] 💾 toSaveData 输入:', {
      blocksCount: blocks.length,
      hasNoteInfo: !!noteInfo,
      noteInfo,
    });
    
    // 计算文本内容
    const textContent = blocks
      .filter(b => b.type !== 'note-info' && !b.isBufferBlock)
      .map(b => {
        if (b.isSummary) {
          return `[SUMMARY_BLOCK_START]${b.content}[SUMMARY_BLOCK_END]`;
        }
        // 图片块：添加占位符到 text 字段
        if (b.type === 'image') {
          return `[IMAGE: ${b.imageUrl || ''}]${b.imageCaption ? ' ' + b.imageCaption : ''}`;
        }
        return b.content;
      })
      .filter(text => text.trim())
      .join('\n');
    
    const result = {
      text: textContent,
      app_type: 'voice-note' as const,
      metadata: {
        blocks,
        noteInfo,
        block_count: blocks.length,
      },
    };
    
    console.log('[VoiceNoteAdapter] 💾 toSaveData 输出:', {
      textLength: result.text.length,
      metadataBlocksCount: result.metadata.blocks.length,
      metadataHasNoteInfo: !!result.metadata.noteInfo,
    });
    
    return result;
  }
  
  /**
   * 检查是否有内容
   */
  hasContent(data: VoiceNoteData): boolean {
    const { blocks, noteInfo } = data;
    
    // 检查是否有有效的 block 内容（排除 note-info 和 buffer block）
    const hasBlockContent = blocks.some(b => 
      b.type !== 'note-info' && 
      !b.isBufferBlock && 
      (b.content?.trim() || b.type === 'image')
    );
    
    // 仅有 noteInfo 不算有效内容（需要至少有一个 block）
    // 这样可以避免在只编辑 note-info 时就触发保存
    return hasBlockContent;
  }
}

