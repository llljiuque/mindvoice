/**
 * 简化版操作转换（Operational Transform）系统
 * 用于处理ASR和用户编辑的协作
 */

export type OperationType = 'insert' | 'delete' | 'replace';

export interface Operation {
  type: OperationType;
  position: number;
  text?: string; // insert/replace 时使用
  length?: number; // delete 时使用
  oldText?: string; // replace 时使用
  timestamp: number; // 操作时间戳
  author: 'asr' | 'user'; // 操作作者
}

/**
 * 操作转换器
 * 将操作转换为可以应用到当前文档的形式
 */
export class OperationTransformer {
  /**
   * 转换操作：将操作 op1 转换为相对于 op2 之后的状态
   * @param op1 要转换的操作
   * @param op2 参考操作（已经应用的操作）
   * @returns 转换后的操作
   */
  static transform(op1: Operation, op2: Operation): Operation {
    // 计算操作的影响范围
    const getOpEnd = (op: Operation): number => {
      if (op.type === 'delete') {
        return op.position + (op.length || 0);
      }
      return op.position + (op.text?.length || op.oldText?.length || 0);
    };
    
    const op1End = getOpEnd(op1);
    const op2End = getOpEnd(op2);
    
    // 如果两个操作不相交
    if (op1End <= op2.position) {
      // op1 在 op2 之前，位置不变
      return op1;
    }
    
    if (op2End <= op1.position) {
      // op2 在 op1 之前，需要调整 op1 的位置
      const op2Length = op2.type === 'delete' 
        ? -(op2.length || 0)
        : (op2.text?.length || op2.oldText?.length || 0);
      
      return {
        ...op1,
        position: Math.max(0, op1.position + op2Length),
      };
    }
    
    // 操作相交，需要特殊处理
    return this.transformConflict(op1, op2);
  }

  /**
   * 处理操作冲突
   */
  private static transformConflict(op1: Operation, op2: Operation): Operation {
    // 简化策略：
    // 1. 如果用户正在编辑，优先保留用户操作
    // 2. ASR操作如果是追加（在末尾），总是可以应用
    // 3. 其他冲突，根据操作类型和位置智能处理
    
    // 如果 op1 是用户操作，op2 是 ASR 操作
    if (op1.author === 'user' && op2.author === 'asr') {
      // 用户操作优先，但需要调整位置
      const op2Length = op2.type === 'delete' 
        ? -(op2.length || 0)
        : (op2.text?.length || op2.oldText?.length || 0);
      
      // 如果 op2 在 op1 之前结束，调整 op1 的位置
      if (op2.position + (op2.length || op2.text?.length || 0) <= op1.position) {
        return {
          ...op1,
          position: op1.position + op2Length,
        };
      }
      
      // 如果 op2 在 op1 之后开始，位置不变
      if (op2.position >= op1.position + (op1.length || op1.text?.length || 0)) {
        return op1;
      }
      
      // 重叠情况：用户操作优先，但需要调整位置
      // 简单策略：将用户操作移到冲突区域之后
      const conflictStart = Math.max(op1.position, op2.position);
      const conflictEnd = Math.min(
        op1.position + (op1.length || op1.text?.length || 0),
        op2.position + (op2.length || op2.text?.length || 0)
      );
      
      return {
        ...op1,
        position: conflictEnd,
      };
    }
    
    // 如果 op1 是 ASR 操作，op2 是用户操作
    if (op1.author === 'asr' && op2.author === 'user') {
      // 用户操作优先，ASR 操作需要调整或跳过
      // 如果 ASR 操作是追加（在文档末尾），可以应用
      // 否则需要调整位置
      
      const op2Length = op2.type === 'delete' 
        ? -(op2.length || 0)
        : (op2.text?.length || op2.oldText?.length || 0);
      
      // 如果 op2 在 op1 之前结束，调整 op1 的位置
      if (op2.position + (op2.length || op2.text?.length || 0) <= op1.position) {
        return {
          ...op1,
          position: op1.position + op2Length,
        };
      }
      
      // 如果 op2 在 op1 之后开始，位置不变
      if (op2.position >= op1.position + (op1.length || op1.text?.length || 0)) {
        return op1;
      }
      
      // 重叠情况：用户编辑优先
      // 如果ASR操作是追加（在文档末尾），仍然可以应用
      const docLength = op2.position + (op2.length || op2.text?.length || 0);
      if (op1.position >= docLength) {
        // ASR操作在用户编辑之后，可以应用，但需要调整位置
        const op2Length = op2.type === 'delete' 
          ? -(op2.length || 0)
          : (op2.text?.length || op2.oldText?.length || 0);
        return {
          ...op1,
          position: op1.position + op2Length,
        };
      }
      
      // 完全重叠：跳过ASR操作（用户编辑优先）
      // 返回一个空操作（实际上不应用）
      return {
        ...op1,
        type: 'insert',
        position: op1.position,
        text: '',
        length: 0,
      };
    }
    
    // 相同作者的操作，按时间戳排序
    if (op1.timestamp < op2.timestamp) {
      // op1 先发生，位置不变
      return op1;
    } else {
      // op2 先发生，调整 op1 的位置
      const op2Length = op2.type === 'delete' 
        ? -(op2.length || 0)
        : (op2.text?.length || op2.oldText?.length || 0);
      
      return {
        ...op1,
        position: op1.position + op2Length,
      };
    }
  }

  /**
   * 应用操作到文档
   */
  static applyOperation(document: string, operation: Operation): string {
    // 空操作（被跳过的操作）不应用
    if (operation.type === 'insert' && (!operation.text || operation.text.length === 0)) {
      return document;
    }
    
    if (operation.type === 'insert' && operation.text) {
      const pos = Math.max(0, Math.min(operation.position, document.length));
      const before = document.slice(0, pos);
      const after = document.slice(pos);
      return before + operation.text + after;
    }
    
    if (operation.type === 'delete' && operation.length && operation.length > 0) {
      const pos = Math.max(0, Math.min(operation.position, document.length));
      const len = Math.min(operation.length, document.length - pos);
      if (len <= 0) return document;
      const before = document.slice(0, pos);
      const after = document.slice(pos + len);
      return before + after;
    }
    
    if (operation.type === 'replace' && operation.oldText && operation.text) {
      const pos = Math.max(0, Math.min(operation.position, document.length));
      const oldLen = Math.min(operation.oldText.length, document.length - pos);
      const before = document.slice(0, pos);
      const after = document.slice(pos + oldLen);
      return before + operation.text + after;
    }
    
    return document;
  }

  /**
   * 将文本差异转换为操作
   * @param oldText 旧文本
   * @param newText 新文本
   * @param author 操作作者
   * @returns 操作列表
   */
  static diffToOperations(oldText: string, newText: string, author: 'asr' | 'user'): Operation[] {
    const operations: Operation[] = [];
    const timestamp = Date.now();
    
    // 简单的差异算法：找到第一个不同的位置
    let i = 0;
    while (i < oldText.length && i < newText.length && oldText[i] === newText[i]) {
      i++;
    }
    
    // 找到最后一个相同的位置（从末尾）
    let j = oldText.length - 1;
    let k = newText.length - 1;
    while (j >= i && k >= i && oldText[j] === newText[k]) {
      j--;
      k--;
    }
    
    // 如果完全替换
    if (i === 0 && j === oldText.length - 1 && k === newText.length - 1) {
      operations.push({
        type: 'replace',
        position: 0,
        oldText: oldText,
        text: newText,
        timestamp,
        author,
      });
      return operations;
    }
    
    // 追加（新文本包含旧文本）
    if (newText.startsWith(oldText)) {
      const appended = newText.slice(oldText.length);
      if (appended) {
        operations.push({
          type: 'insert',
          position: oldText.length,
          text: appended,
          timestamp,
          author,
        });
      }
      return operations;
    }
    
    // 删除（旧文本包含新文本）
    if (oldText.startsWith(newText)) {
      const deleted = oldText.slice(newText.length);
      if (deleted) {
        operations.push({
          type: 'delete',
          position: newText.length,
          length: deleted.length,
          timestamp,
          author,
        });
      }
      return operations;
    }
    
    // 中间修改
    const deleted = oldText.slice(i, j + 1);
    const inserted = newText.slice(i, k + 1);
    
    if (deleted) {
      operations.push({
        type: 'delete',
        position: i,
        length: deleted.length,
        timestamp,
        author,
      });
    }
    
    if (inserted) {
      operations.push({
        type: 'insert',
        position: i,
        text: inserted,
        timestamp: timestamp + 1, // 确保顺序
        author,
      });
    }
    
    return operations;
  }

  /**
   * 转换操作序列
   * 将操作序列 op1s 转换为相对于已应用的操作序列 op2s 之后的状态
   */
  static transformOperations(
    op1s: Operation[],
    op2s: Operation[]
  ): Operation[] {
    let transformed = [...op1s];
    
    // 对每个已应用的操作，转换待应用的操作
    for (const op2 of op2s) {
      transformed = transformed.map(op1 => this.transform(op1, op2));
    }
    
    return transformed;
  }
}

