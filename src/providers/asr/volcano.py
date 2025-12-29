"""
火山引擎 ASR 提供商实现
基于 ChefMate 3 项目的 asr_client.py
"""
import asyncio
import aiohttp
import struct
import gzip
import uuid
import json
import logging
from typing import Dict, Any, Optional, Callable
from ..asr.base_asr import BaseASRProvider

logger = logging.getLogger(__name__)

# 火山ASR协议相关常量
class ProtocolVersion:
    V1 = 0b0001

class MessageType:
    CLIENT_FULL_REQUEST = 0b0001
    CLIENT_AUDIO_ONLY_REQUEST = 0b0010
    SERVER_FULL_RESPONSE = 0b1001
    SERVER_ERROR_RESPONSE = 0b1111

class MessageTypeSpecificFlags:
    NO_SEQUENCE = 0b0000
    POS_SEQUENCE = 0b0001
    NEG_SEQUENCE = 0b0010
    NEG_WITH_SEQUENCE = 0b0011

class SerializationType:
    NO_SERIALIZATION = 0b0000
    JSON = 0b0001

class CompressionType:
    GZIP = 0b0001


class AsrRequestHeader:
    """协议头构造"""
    def __init__(self):
        self.message_type = MessageType.CLIENT_FULL_REQUEST
        self.message_type_specific_flags = MessageTypeSpecificFlags.POS_SEQUENCE
        self.serialization_type = SerializationType.JSON
        self.compression_type = CompressionType.GZIP
        self.reserved_data = bytes([0x00])

    def with_message_type(self, message_type: int):
        self.message_type = message_type
        return self

    def with_message_type_specific_flags(self, flags: int):
        self.message_type_specific_flags = flags
        return self

    def with_serialization_type(self, serialization_type: int):
        self.serialization_type = serialization_type
        return self

    def with_compression_type(self, compression_type: int):
        self.compression_type = compression_type
        return self

    def to_bytes(self) -> bytes:
        header = bytearray()
        header.append((ProtocolVersion.V1 << 4) | 1)
        header.append((self.message_type << 4) | self.message_type_specific_flags)
        header.append((self.serialization_type << 4) | self.compression_type)
        header.extend(self.reserved_data)
        return bytes(header)

    @staticmethod
    def default_header():
        return AsrRequestHeader()


class RequestBuilder:
    """请求构造"""
    @staticmethod
    def new_auth_headers(access_key: str, app_key: str) -> dict:
        reqid = str(uuid.uuid4())
        return {
            "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
            "X-Api-Request-Id": reqid,
            "X-Api-Access-Key": access_key,
            "X-Api-App-Key": app_key
        }

    @staticmethod
    def new_full_client_request(seq: int) -> bytes:
        header = AsrRequestHeader.default_header() \
            .with_message_type_specific_flags(MessageTypeSpecificFlags.POS_SEQUENCE)
        
        payload = {
            "user": {"uid": "demo_uid"},
            "audio": {
                "format": "pcm",
                "codec": "raw",
                "rate": 16000,
                "bits": 16,
                "channel": 1
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "enable_ddc": True,
                "show_utterances": True,
                "result_type": "single",
                "vad_segment_duration": 600,
                "enable_nonstream": False
            }
        }
        payload_bytes = json.dumps(payload).encode('utf-8')
        compressed_payload = gzip.compress(payload_bytes)
        payload_size = len(compressed_payload)
        
        req = bytearray()
        req.extend(header.to_bytes())
        req.extend(struct.pack('>i', seq))
        req.extend(struct.pack('>I', payload_size))
        req.extend(compressed_payload)
        return bytes(req)

    @staticmethod
    def new_audio_only_request(seq: int, segment: bytes, is_last: bool = False) -> bytes:
        header = AsrRequestHeader.default_header().with_message_type(MessageType.CLIENT_AUDIO_ONLY_REQUEST)
        if is_last:
            header.with_message_type_specific_flags(MessageTypeSpecificFlags.NEG_WITH_SEQUENCE)
            seq = -seq
        else:
            header.with_message_type_specific_flags(MessageTypeSpecificFlags.POS_SEQUENCE)
        
        req = bytearray()
        req.extend(header.to_bytes())
        req.extend(struct.pack('>i', seq))
        compressed_segment = gzip.compress(segment)
        req.extend(struct.pack('>I', len(compressed_segment)))
        req.extend(compressed_segment)
        return bytes(req)


class AsrResponse:
    """响应解析"""
    def __init__(self):
        self.code = 0
        self.event = 0
        self.is_last_package = False
        self.payload_sequence = 0
        self.payload_size = 0
        self.payload_msg = None
        self.message_type_specific_flags = 0


class ResponseParser:
    """响应解析器"""
    @staticmethod
    def parse_response(msg: bytes) -> AsrResponse:
        response = AsrResponse()
        
        try:
            if len(msg) < 4:
                logger.error("响应消息太短")
                return response
            
            header_size_words = msg[0] & 0x0F
            message_type = (msg[1] >> 4) & 0x0F
            message_type_specific_flags = msg[1] & 0x0F
            serialization_type = (msg[2] >> 4) & 0x0F
            compression_type = msg[2] & 0x0F
            
            response.message_type_specific_flags = message_type_specific_flags
            
            offset = header_size_words * 4
            payload = msg[offset:]
            
            if message_type_specific_flags & 0x01:
                if len(payload) < 4:
                    return response
                response.payload_sequence = struct.unpack('>i', payload[:4])[0]
                payload = payload[4:]
            
            if message_type_specific_flags & 0x02:
                response.is_last_package = True
            
            if message_type_specific_flags & 0x04:
                if len(payload) < 4:
                    return response
                response.event = struct.unpack('>i', payload[:4])[0]
                payload = payload[4:]
            
            if message_type == MessageType.SERVER_FULL_RESPONSE:
                if len(payload) < 4:
                    return response
                response.payload_size = struct.unpack('>I', payload[:4])[0]
                payload = payload[4:]
            elif message_type == MessageType.SERVER_ERROR_RESPONSE:
                if len(payload) < 8:
                    return response
                response.code = struct.unpack('>i', payload[:4])[0]
                response.payload_size = struct.unpack('>I', payload[4:8])[0]
                payload = payload[8:]
            
            if not payload:
                return response
            
            if compression_type == CompressionType.GZIP:
                try:
                    payload = gzip.decompress(payload)
                except Exception as e:
                    logger.error(f"Failed to decompress payload: {e}")
                    return response
            
            try:
                if serialization_type == SerializationType.JSON:
                    response.payload_msg = json.loads(payload.decode('utf-8'))
            except Exception as e:
                logger.error(f"Failed to parse payload: {e}")
                return response
        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            return response
        
        return response


class VolcanoASRProvider(BaseASRProvider):
    """火山引擎 ASR 提供商"""
    
    PROVIDER_NAME = "volcano"
    
    def __init__(self):
        super().__init__()
        self.base_url = ""
        self.app_id = ""
        self.app_key = ""
        self.access_key = ""
        self.session: Optional[aiohttp.ClientSession] = None
        self.conn = None
        self.seq = 1
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._result_text = ""
        self._is_final = False
        self._recognition_event: Optional[asyncio.Event] = None
        
        # 流式识别相关
        self._streaming_active = False
        self._stopping = False  # 标记是否正在停止流式识别
        self._receive_task: Optional[asyncio.Task] = None
        self._on_text_callback: Optional[Callable[[str, bool], None]] = None  # (text, is_final)
        self._accumulated_text = ""  # 累积的所有分句的文本
        self._current_segment_text = ""  # 当前分句的文本
        self._last_final_text = ""  # 上一个分句的最终文本，用于检测新分句
        self._last_segment_text = ""  # 上一个分句的文本（包括中间结果），用于检测新分句和累积
    
    @property
    def name(self) -> str:
        return "volcano"
    
    @property
    def supported_languages(self) -> list[str]:
        return ["zh-CN", "en-US"]
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化火山引擎 ASR"""
        self.base_url = config.get('base_url', 'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel')
        self.app_id = config.get('app_id', '')
        # 优先使用 app_key，如果没有则使用 app_id
        self.app_key = config.get('app_key', '') or config.get('app_id', '')
        self.access_key = config.get('access_key', '')
        
        if not self.access_key or not self.access_key.strip():
            logger.error("火山引擎 ASR 配置不完整：缺少 access_key")
            logger.error("请检查 config.yml 中的 asr.access_key 配置")
            return False
        
        if not self.app_key or not self.app_key.strip():
            logger.error("火山引擎 ASR 配置不完整：缺少 app_key 或 app_id")
            logger.error("请检查 config.yml 中的 asr.app_key 或 asr.app_id 配置")
            return False
        
        logger.info(f"[ASR] 初始化配置: base_url={self.base_url}")
        logger.info(f"[ASR] app_id={self.app_id if self.app_id else '(未设置)'}")
        logger.info(f"[ASR] app_key={'已设置 (' + str(len(self.app_key)) + ' 字符)' if self.app_key else '未设置'}")
        logger.info(f"[ASR] access_key={'已设置 (' + str(len(self.access_key)) + ' 字符)' if self.access_key else '未设置'}")
        
        return super().initialize(config)
    
    async def _connect(self) -> bool:
        """连接 ASR 服务"""
        # 验证凭证格式
        if not self.access_key or not self.access_key.strip():
            logger.error("[ASR] 认证失败: access_key 为空，请检查 config.yml")
            return False
        
        if not self.app_key or not self.app_key.strip():
            logger.error("[ASR] 认证失败: app_key 为空，请检查 config.yml")
            return False
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                headers = RequestBuilder.new_auth_headers(self.access_key, self.app_key)
                logger.info(f"[ASR] 连接尝试 {attempt + 1}/{max_retries}")
                logger.info(f"[ASR] 认证信息: access_key={self.access_key[:8]}...{self.access_key[-4:] if len(self.access_key) > 12 else '***'}, "
                           f"app_key={self.app_key[:8]}...{self.app_key[-4:] if len(self.app_key) > 12 else '***'}")
                
                timeout = aiohttp.ClientTimeout(total=30)
                
                if self.session and not self.session.closed:
                    await self.session.close()
                self.session = aiohttp.ClientSession(timeout=timeout)
                
                logger.info(f"[ASR] 连接URL: {self.base_url}")
                self.conn = await self.session.ws_connect(self.base_url, headers=headers)
                logger.info(f"[ASR] WebSocket连接成功")
                
                self._loop = asyncio.get_event_loop()
                
                logger.info(f"成功连接到火山引擎 ASR 服务: {self.base_url}")
                return True
                
            except aiohttp.ClientResponseError as e:
                error_msg = f"HTTP错误 {e.status}: {e.message}"
                if e.status == 403:
                    error_msg += " (认证失败，请检查 access_key 和 app_key 是否正确)"
                    error_msg += "\n提示：请确认："
                    error_msg += "\n  1. access_key 和 app_key 是否从火山引擎控制台正确获取"
                    error_msg += "\n  2. 凭证是否已过期或已被撤销"
                    error_msg += "\n  3. 凭证是否有访问 ASR 服务的权限"
                    error_msg += f"\n  4. 当前使用的 access_key 前8位: {self.access_key[:8]}..."
                    error_msg += f"\n  5. 当前使用的 app_key 前8位: {self.app_key[:8]}..."
                logger.error(f"[ASR] 连接错误 (第{attempt + 1}次尝试): {error_msg}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"[ASR] 连接最终失败: {error_msg}")
                    return False
                    
            except asyncio.TimeoutError as e:
                logger.warning(f"[ASR] 连接超时 (第{attempt + 1}次尝试): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"[ASR] 连接最终超时，所有重试失败")
                    return False
                    
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"[ASR] 连接错误 (第{attempt + 1}次尝试): {error_msg}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"[ASR] 连接最终失败: {error_msg}")
                    return False
        
        return False
    
    async def _disconnect(self):
        """断开连接"""
        try:
            if self.conn and not self.conn.closed:
                await self.conn.close()
            if self.session and not self.session.closed:
                await self.session.close()
        except Exception as e:
            logger.error(f"断开连接失败: {e}")
    
    async def _send_full_request(self):
        """发送完整客户端请求"""
        try:
            request = RequestBuilder.new_full_client_request(self.seq)
            await self.conn.send_bytes(request)
            self.seq += 1
        except Exception as e:
            logger.error(f"发送完整客户端请求失败: {e}")
            raise
    
    async def _send_audio_data(self, audio_data: bytes, is_last: bool = False):
        """发送音频数据"""
        try:
            if not self.conn or self.conn.closed:
                logger.error("[ASR] 连接已关闭或不可用，无法发送音频数据")
                return
            request = RequestBuilder.new_audio_only_request(self.seq, audio_data, is_last)
            request_size = len(request)
            logger.info(f"[ASR] 发送音频数据: seq={self.seq}, 音频大小={len(audio_data)}字节, 请求大小={request_size}字节, is_last={is_last}")
            await self.conn.send_bytes(request)
            self.seq += 1
            logger.debug(f"[ASR] 音频数据已发送，下一个seq={self.seq}")
        except Exception as e:
            logger.error(f"[ASR] 发送音频数据失败: {e}", exc_info=True)
    
    async def _receive_results(self):
        """接收 ASR 结果"""
        try:
            async for msg in self.conn:
                logger.debug(f"[ASR] 收到消息类型: {msg.type}")
                if msg.type == aiohttp.WSMsgType.BINARY:
                    try:
                        response = ResponseParser.parse_response(msg.data)
                        
                        is_last_audio_package = (response.is_last_package or 
                                               response.message_type_specific_flags == 0b0011)
                        
                        logger.debug(f"[ASR] 响应解析: code={response.code}, "
                                   f"is_last_package={response.is_last_package}, "
                                   f"is_last_audio_package={is_last_audio_package}")
                        
                        if response.payload_msg:
                            result = response.payload_msg.get('result', {})
                            text = result.get('text', '') if isinstance(result, dict) else ''
                            
                            is_final = (
                                bool(result.get('is_final')) if isinstance(result, dict) else False
                            ) or bool(response.payload_msg.get('is_final', False)) or is_last_audio_package
                            
                            logger.debug(f"[ASR] 收到识别结果: '{text}', 是否最终: {is_final}")
                            
                            if text:
                                if is_final:
                                    # 最终结果
                                    self._result_text = text
                                    self._is_final = True
                                    logger.info(f"[ASR] 最终结果: '{text}'")
                                    if self._recognition_event:
                                        self._recognition_event.set()
                                else:
                                    # 中间结果累积（用于实时显示）
                                    if not self._result_text:
                                        self._result_text = text
                                    else:
                                        # 如果新文本包含旧文本，只取新增部分
                                        if text.startswith(self._result_text):
                                            self._result_text = text
                                        else:
                                            # 否则直接替换（可能是重新识别）
                                            self._result_text = text
                                    logger.debug(f"[ASR] 中间结果: '{self._result_text}'")
                        
                        if response.code != 0:
                            error_reasons = {
                                1001: "参数错误",
                                1002: "认证失败",
                                1003: "配额超限",
                                1004: "服务不可用",
                                1005: "内部错误",
                                1006: "请求超时",
                                1007: "音频格式错误",
                                1008: "音频长度错误",
                                1009: "音频采样率错误",
                                1010: "音频声道数错误"
                            }
                            reason = error_reasons.get(response.code, f"未知错误码: {response.code}")
                            logger.error(f"[ASR] 错误码: {response.code}, 原因: {reason}")
                            if self._recognition_event:
                                self._recognition_event.set()
                            break
                        
                        if is_last_audio_package:
                            logger.debug(f"[ASR] 接收结束: is_last_audio_package={is_last_audio_package}")
                            if self._recognition_event:
                                self._recognition_event.set()
                            break
                    except Exception as e:
                        logger.error(f"[ASR] 解析响应失败: {e}", exc_info=True)
                        continue
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"[ASR] WebSocket错误: {msg.data}")
                    if self._recognition_event:
                        self._recognition_event.set()
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("[ASR] WebSocket连接已关闭")
                    if self._recognition_event:
                        self._recognition_event.set()
                    break
        except Exception as e:
            logger.error(f"[ASR] 接收结果异常: {e}", exc_info=True)
            if self._recognition_event:
                self._recognition_event.set()
    
    def recognize(self, audio_data: bytes, language: str = "zh-CN", **kwargs) -> str:
        """识别音频（同步接口，内部使用异步）"""
        if not self._initialized:
            return ""
        
        # 使用事件循环运行异步识别
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._recognize_async(audio_data, language))
    
    async def _recognize_async(self, audio_data: bytes, language: str = "zh-CN") -> str:
        """异步识别音频"""
        self._result_text = ""
        self._is_final = False
        self._recognition_event = asyncio.Event()
        self.seq = 1
        
        # 连接
        if not await self._connect():
            logger.error("[ASR] 连接失败，无法进行识别")
            return ""
        
        receive_task = None
        try:
            # 发送完整请求
            logger.debug("[ASR] 发送完整客户端请求")
            await self._send_full_request()
            await asyncio.sleep(0.2)
            
            # 启动结果接收任务
            logger.debug("[ASR] 启动结果接收任务")
            receive_task = asyncio.create_task(self._receive_results())
            await asyncio.sleep(0.2)
            
            # 发送音频数据
            logger.info(f"[ASR] 准备发送音频数据进行识别，长度: {len(audio_data)} 字节")
            await self._send_audio_data(audio_data, is_last=True)
            logger.info("[ASR] 音频数据已发送，等待识别结果...")
            
            # 等待结果（最多10秒）
            try:
                await asyncio.wait_for(self._recognition_event.wait(), timeout=10.0)
                logger.debug("[ASR] 收到识别结果信号")
            except asyncio.TimeoutError:
                logger.warning("[ASR] 识别超时")
            
            # 等待接收任务完成
            await asyncio.sleep(0.5)
            if receive_task and not receive_task.done():
                receive_task.cancel()
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass
            
            logger.info(f"[ASR] 识别完成，结果: '{self._result_text}'")
            return self._result_text
        except Exception as e:
            logger.error(f"[ASR] 识别过程出错: {e}")
            return ""
        finally:
            await self._disconnect()
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._initialized and bool(self.access_key and self.app_key)
    
    def set_on_text_callback(self, callback: Optional[Callable[[str, bool], None]]):
        """设置文本回调函数（用于流式识别）
        
        Args:
            callback: 回调函数，参数为 (text: str, is_final: bool)
        """
        self._on_text_callback = callback
    
    async def start_streaming_recognition(self, language: str = "zh-CN") -> bool:
        """开始流式识别"""
        if self._streaming_active:
            logger.warning("[ASR] 流式识别已在进行中")
            return False
        
        # 连接
        if not await self._connect():
            logger.error("[ASR] 连接失败，无法开始流式识别")
            return False
        
        try:
            # 重置状态
            self._accumulated_text = ""
            self._current_segment_text = ""
            self._last_final_text = ""
            self._last_segment_text = ""
            self._result_text = ""
            self._is_final = False
            self._stopping = False
            self.seq = 1
            self._recognition_event = asyncio.Event()
            
            # 发送完整请求
            logger.debug("[ASR] 发送完整客户端请求（流式）")
            await self._send_full_request()
            await asyncio.sleep(0.2)
            
            # 启动结果接收任务
            logger.debug("[ASR] 启动流式结果接收任务")
            self._receive_task = asyncio.create_task(self._receive_streaming_results())
            await asyncio.sleep(0.2)
            
            self._streaming_active = True
            logger.info("[ASR] 流式识别已启动")
            return True
        except Exception as e:
            logger.error(f"[ASR] 启动流式识别失败: {e}")
            await self._disconnect()
            return False
    
    async def send_audio_chunk(self, audio_data: bytes):
        """发送音频数据块（流式）"""
        if not self._streaming_active or not self.conn or self.conn.closed:
            logger.warning("[ASR] 流式识别未激活或连接已关闭，无法发送音频数据块")
            return
        
        try:
            logger.debug(f"[ASR] 发送音频数据块: {len(audio_data)} 字节")
            await self._send_audio_data(audio_data, is_last=False)
        except Exception as e:
            logger.error(f"[ASR] 发送音频数据块失败: {e}", exc_info=True)
    
    async def stop_streaming_recognition(self) -> str:
        """停止流式识别并返回最终结果"""
        if not self._streaming_active:
            logger.warning("[ASR] 流式识别未激活")
            return self._accumulated_text
        
        try:
            # 标记正在停止
            self._stopping = True
            logger.debug("[ASR] 标记流式识别为停止状态")
            
            # 发送结束信号
            logger.debug("[ASR] 发送流式识别结束信号")
            await self._send_audio_data(b"", is_last=True)
            
            # 等待最终结果（最多2秒）
            if self._recognition_event:
                try:
                    await asyncio.wait_for(self._recognition_event.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning("[ASR] 等待最终结果超时")
            
            # 等待接收任务完成
            await asyncio.sleep(0.5)
            if self._receive_task and not self._receive_task.done():
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass
            
            # 合并最终文本
            final_text = self._accumulated_text + self._current_segment_text
            logger.info(f"[ASR] 流式识别完成，最终结果: '{final_text}'")
            
            return final_text
        except Exception as e:
            logger.error(f"[ASR] 停止流式识别失败: {e}")
            return self._accumulated_text
        finally:
            self._streaming_active = False
            self._stopping = False
            await self._disconnect()
    
    async def _receive_streaming_results(self):
        """接收流式识别结果"""
        try:
            async for msg in self.conn:
                logger.debug(f"[ASR] 收到消息类型: {msg.type}")
                if msg.type == aiohttp.WSMsgType.BINARY:
                    try:
                        response = ResponseParser.parse_response(msg.data)
                        
                        is_last_audio_package = (response.is_last_package or 
                                               response.message_type_specific_flags == 0b0011)
                        
                        if response.payload_msg:
                            result = response.payload_msg.get('result', {})
                            text = result.get('text', '') if isinstance(result, dict) else ''
                            
                            is_final = (
                                bool(result.get('is_final')) if isinstance(result, dict) else False
                            ) or bool(response.payload_msg.get('is_final', False)) or is_last_audio_package
                            
                            if text:
                                if is_final:
                                    # 最终结果：ASR按分句返回累积文本
                                    # 每个分句结束时，ASR返回的是该分句的文本（可能包含该分句的重复，如"你好。你好。你好。"）
                                    # 但不包含之前分句的文本
                                    
                                    # 检测是否是新分句
                                    # ASR按分句返回文本，每个分句结束时返回该分句的最终文本
                                    # 简化逻辑：如果新文本不是以上一个分句开头，就认为是新分句
                                    is_new_segment = False
                                    if self._last_final_text:
                                        # 如果新文本以上一个分句开头，说明是同一分句的更新
                                        # 否则是新分句
                                        if text.startswith(self._last_final_text):
                                            # 同一分句的更新（ASR可能重复返回或扩展）
                                            is_new_segment = False
                                        else:
                                            # 新分句
                                            is_new_segment = True
                                    else:
                                        # 第一个分句
                                        is_new_segment = True
                                    
                                    logger.debug(f"[ASR] 分句检测: 上一个='{self._last_final_text}', 当前='{text}', 是否新分句={is_new_segment}")
                                    
                                    if is_new_segment:
                                        # 新分句：将之前累积的所有分句文本加上新分句
                                        if self._accumulated_text:
                                            # 添加空格分隔不同分句
                                            if not self._accumulated_text.endswith(' ') and not self._accumulated_text.endswith('\n'):
                                                self._accumulated_text += " "
                                        old_accumulated = self._accumulated_text
                                        self._accumulated_text += text
                                        logger.info(f"[ASR] 新分句完成: 上一个分句='{self._last_final_text}', 新分句='{text}', 累积前='{old_accumulated}', 累积后='{self._accumulated_text}'")
                                    else:
                                        # 同一分句的更新：ASR可能重复返回同一分句的累积文本
                                        # 如果新文本与上一个不同，更新当前分句
                                        if text != self._last_final_text:
                                            # 从累积文本中移除上一个分句，添加新分句
                                            # 注意：这里假设上一个分句在累积文本的末尾
                                            if self._accumulated_text.endswith(self._last_final_text):
                                                self._accumulated_text = self._accumulated_text[:-len(self._last_final_text)].rstrip()
                                                if self._accumulated_text and not self._accumulated_text.endswith(' '):
                                                    self._accumulated_text += " "
                                                self._accumulated_text += text
                                            else:
                                                # 如果无法精确匹配，直接追加（这种情况不应该发生）
                                                if self._accumulated_text and not self._accumulated_text.endswith(' '):
                                                    self._accumulated_text += " "
                                                self._accumulated_text += text
                                            logger.debug(f"[ASR] 分句更新: '{text}' -> 累积: '{self._accumulated_text}'")
                                        # 如果完全相同，不做任何操作
                                    
                                    self._current_segment_text = ""
                                    self._last_final_text = text
                                    self._last_segment_text = text  # 也更新上一个分句的文本
                                    final_text = self._accumulated_text
                                    
                                    # 回调最终结果（传递累积的所有分句文本）
                                    logger.info(f"[ASR] 准备回调最终结果: 累积文本='{final_text}'")
                                    if self._on_text_callback:
                                        self._on_text_callback(final_text, True)
                                        logger.info(f"[ASR] 已调用回调函数")
                                    
                                    # 注意：不设置 _recognition_event，因为流式识别还在继续
                                    # _recognition_event 只在流式识别真正结束时设置（错误、连接关闭、主动停止）
                                else:
                                    # 中间结果：更新当前片段
                                    # 检测是否是新分句的开始
                                    is_new_segment_start = False
                                    if self._last_segment_text:
                                        # 如果新文本不包含上一个分句的文本，说明是新分句的开始
                                        # 使用 startswith 检查，因为新分句通常不会以上一个分句开头
                                        if not text.startswith(self._last_segment_text):
                                            # 进一步检查：如果新文本完全不包含上一个分句的任何部分，肯定是新分句
                                            # 或者新文本的开头与上一个分句完全不同
                                            last_words = self._last_segment_text.split()[:2] if self._last_segment_text else []
                                            if last_words:
                                                last_start = ' '.join(last_words)
                                                if not text.startswith(last_start):
                                                    is_new_segment_start = True
                                            else:
                                                # 如果上一个分句很短或为空，直接比较
                                                if self._last_segment_text not in text:
                                                    is_new_segment_start = True
                                    else:
                                        # 第一个分句
                                        is_new_segment_start = True
                                    
                                    if is_new_segment_start:
                                        # 新分句的开始：将上一个分句的文本累积起来（如果还没有累积）
                                        # 优先使用 _last_final_text（如果有），否则使用 _last_segment_text
                                        segment_to_accumulate = self._last_final_text if self._last_final_text else self._last_segment_text
                                        
                                        if segment_to_accumulate and segment_to_accumulate not in self._accumulated_text:
                                            # 上一个分句还没有被累积，现在累积它
                                            if self._accumulated_text:
                                                if not self._accumulated_text.endswith(' ') and not self._accumulated_text.endswith('\n'):
                                                    self._accumulated_text += " "
                                            self._accumulated_text += segment_to_accumulate
                                            logger.info(f"[ASR] 检测到新分句，累积上一个分句: '{segment_to_accumulate}' -> 累积: '{self._accumulated_text}'")
                                        
                                        # 更新当前片段
                                        self._current_segment_text = text
                                        self._last_segment_text = text
                                        
                                        # 新分句的中间结果：累积之前的分句加上当前分句
                                        display_text = (self._accumulated_text + " " + self._current_segment_text) if self._accumulated_text else self._current_segment_text
                                    else:
                                        # 同一分句的中间结果：更新当前片段
                                        self._current_segment_text = text
                                        self._last_segment_text = text
                                        
                                        # 同一分句的中间结果：累积之前的分句加上当前分句
                                        display_text = (self._accumulated_text + self._current_segment_text) if self._accumulated_text else self._current_segment_text
                                    
                                    logger.debug(f"[ASR] 流式中间结果: '{display_text}'")
                                    
                                    # 回调中间结果
                                    if self._on_text_callback:
                                        self._on_text_callback(display_text, False)
                        
                        if response.code != 0:
                            error_reasons = {
                                1001: "参数错误",
                                1002: "认证失败",
                                1003: "配额超限",
                                1004: "服务不可用",
                                1005: "内部错误",
                                1006: "请求超时",
                                1007: "音频格式错误",
                                1008: "音频长度错误",
                                1009: "音频采样率错误",
                                1010: "音频声道数错误"
                            }
                            reason = error_reasons.get(response.code, f"未知错误码: {response.code}")
                            logger.error(f"[ASR] 错误码: {response.code}, 原因: {reason}")
                            if self._recognition_event:
                                self._recognition_event.set()
                            break
                        
                        # 注意：is_last_audio_package 只表示一个语音片段的结束，不是整个流式识别会话的结束
                        # 对于长时间运行的语音记事本，应该继续接收后续的音频识别结果
                        # 只有当流式识别被主动停止（self._stopping = True）或连接关闭时，才退出循环
                        if is_last_audio_package:
                            if self._stopping:
                                # 用户主动停止，设置事件并退出循环
                                logger.debug(f"[ASR] 收到停止信号，结束流式识别")
                                if self._recognition_event:
                                    self._recognition_event.set()
                                break
                            else:
                                # 正常的语音片段结束，继续接收后续的音频识别结果
                                logger.debug(f"[ASR] 当前语音片段结束，继续等待后续音频")
                    except Exception as e:
                        logger.error(f"[ASR] 解析流式响应失败: {e}", exc_info=True)
                        continue
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"[ASR] WebSocket错误: {msg.data}")
                    if self._recognition_event:
                        self._recognition_event.set()
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("[ASR] WebSocket连接已关闭")
                    if self._recognition_event:
                        self._recognition_event.set()
                    break
        except Exception as e:
            logger.error(f"[ASR] 接收流式结果异常: {e}", exc_info=True)
            if self._recognition_event:
                self._recognition_event.set()
