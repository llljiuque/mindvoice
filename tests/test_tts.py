#!/usr/bin/env python3
"""
TTS功能自动化测试脚本

使用方法:
    python tests/test_tts.py
"""
import requests
import json
import sys
from pathlib import Path

API_BASE = "http://127.0.0.1:8765"
TIMEOUT = 30  # 30秒超时


def test_tts_voices():
    """测试获取音色列表"""
    print("\n[测试1] 获取音色列表...")
    try:
        response = requests.get(f"{API_BASE}/api/tts/voices", timeout=TIMEOUT)
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()
        assert data["success"] == True, f"响应格式错误: {data}"
        assert "voices" in data, "缺少voices字段"
        assert isinstance(data["voices"], list), "voices不是列表"
        print(f"✓ 音色列表测试通过，找到 {len(data['voices'])} 个音色")
        if data["voices"]:
            print(f"  示例音色: {data['voices'][0]}")
        return True
    except Exception as e:
        print(f"✗ 音色列表测试失败: {e}")
        return False


def test_tts_synthesize():
    """测试文本转语音"""
    print("\n[测试2] 文本转语音（非流式）...")
    try:
        payload = {
            "text": "你好，这是自动化测试。",
            "language": "zh-CN",
            "speed": 1.0
        }
        response = requests.post(
            f"{API_BASE}/api/tts/synthesize",
            json=payload,
            timeout=TIMEOUT
        )
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        assert response.headers.get("content-type") == "audio/wav", f"Content-Type错误: {response.headers.get('content-type')}"
        
        # 保存音频文件用于验证
        output_file = Path("test_output.wav")
        output_file.write_bytes(response.content)
        file_size = len(response.content)
        print(f"✓ 文本转语音测试通过")
        print(f"  音频文件大小: {file_size} 字节 ({file_size/1024:.2f} KB)")
        print(f"  音频文件已保存: {output_file.absolute()}")
        return True
    except Exception as e:
        print(f"✗ 文本转语音测试失败: {e}")
        return False


def test_tts_stream():
    """测试流式语音合成"""
    print("\n[测试3] 流式语音合成...")
    try:
        payload = {
            "text": "这是一段较长的文本，用于测试流式语音合成功能。流式合成可以实时返回音频数据块，提供更好的用户体验。",
            "language": "zh-CN",
            "speed": 1.0
        }
        response = requests.post(
            f"{API_BASE}/api/tts/stream",
            json=payload,
            stream=True,
            timeout=TIMEOUT
        )
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        assert response.headers.get("content-type") == "audio/wav", f"Content-Type错误: {response.headers.get('content-type')}"
        
        # 收集流式数据
        chunks = []
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                chunks.append(chunk)
        
        # 保存音频文件
        output_file = Path("test_stream.wav")
        audio_data = b''.join(chunks)
        output_file.write_bytes(audio_data)
        file_size = len(audio_data)
        print(f"✓ 流式语音合成测试通过")
        print(f"  音频文件大小: {file_size} 字节 ({file_size/1024:.2f} KB)")
        print(f"  音频文件已保存: {output_file.absolute()}")
        print(f"  接收到的数据块数: {len(chunks)}")
        return True
    except Exception as e:
        print(f"✗ 流式语音合成测试失败: {e}")
        return False


def test_tts_multilanguage():
    """测试多语言支持"""
    print("\n[测试4] 多语言支持...")
    languages = [
        ("zh-CN", "你好，这是中文测试。"),
        ("en-US", "Hello, this is an English test."),
    ]
    
    success_count = 0
    for lang, text in languages:
        try:
            payload = {
                "text": text,
                "language": lang,
                "speed": 1.0
            }
            response = requests.post(
                f"{API_BASE}/api/tts/synthesize",
                json=payload,
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                print(f"  ✓ {lang}: 成功")
                success_count += 1
            else:
                print(f"  ✗ {lang}: 失败 (状态码: {response.status_code})")
        except Exception as e:
            print(f"  ✗ {lang}: 失败 ({e})")
    
    return success_count == len(languages)


def test_tts_error_handling():
    """测试错误处理"""
    print("\n[测试5] 错误处理...")
    tests_passed = 0
    total_tests = 0
    
    # 测试1: 空文本（FastAPI返回422表示Pydantic验证失败，这是正常的）
    total_tests += 1
    try:
        payload = {"text": "", "language": "zh-CN"}
        response = requests.post(
            f"{API_BASE}/api/tts/synthesize",
            json=payload,
            timeout=TIMEOUT
        )
        # FastAPI的Pydantic验证失败会返回422，这是正常的
        if response.status_code in [400, 422]:
            print(f"  ✓ 空文本验证: 正确返回{response.status_code}错误")
            tests_passed += 1
        else:
            print(f"  ✗ 空文本验证: 期望400或422，实际{response.status_code}")
    except Exception as e:
        print(f"  ✗ 空文本验证失败: {e}")
    
    # 测试2: 无效语速（speed=3.0超出范围，Pydantic会返回422）
    total_tests += 1
    try:
        payload = {"text": "测试", "language": "zh-CN", "speed": 3.0}
        response = requests.post(
            f"{API_BASE}/api/tts/synthesize",
            json=payload,
            timeout=TIMEOUT
        )
        # Pydantic验证：speed字段有ge=0.5, le=2.0限制，超出范围会返回422
        if response.status_code in [400, 422]:
            print(f"  ✓ 无效语速处理: 正确返回{response.status_code}错误")
            tests_passed += 1
        elif response.status_code == 200:
            # 如果服务端自动限制范围，也可以接受
            print("  ✓ 无效语速处理: 服务端自动限制范围")
            tests_passed += 1
        else:
            print(f"  ✗ 无效语速处理: 状态码{response.status_code}")
    except Exception as e:
        print(f"  ✗ 无效语速处理失败: {e}")
    
    return tests_passed == total_tests


def test_tts_providers():
    """测试获取TTS提供商列表"""
    print("\n[测试0] 获取TTS提供商列表...")
    try:
        response = requests.get(f"{API_BASE}/api/tts/providers", timeout=TIMEOUT)
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.json()
        assert data["success"] == True, f"响应格式错误: {data}"
        assert "providers" in data, "缺少providers字段"
        assert isinstance(data["providers"], list), "providers不是列表"
        assert len(data["providers"]) > 0, "提供商列表为空"
        
        print(f"✓ 提供商列表测试通过，找到 {len(data['providers'])} 个提供商")
        for provider in data["providers"]:
            print(f"  - {provider.get('name')}: {provider.get('display_name')}")
        
        # 检查当前提供商
        if "current" in data:
            print(f"  当前使用的提供商: {data['current']}")
        
        return True
    except Exception as e:
        print(f"✗ 提供商列表测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("TTS 功能自动化测试（模块化版本）")
    print("=" * 60)
    print(f"API地址: {API_BASE}")
    print(f"超时设置: {TIMEOUT}秒")
    
    # 检查服务器是否可用
    try:
        response = requests.get(f"{API_BASE}/api/status", timeout=5)
        if response.status_code != 200:
            print(f"\n✗ 服务器不可用，状态码: {response.status_code}")
            print("请先启动API服务器: python api_server.py")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\n✗ 无法连接到API服务器")
        print("请先启动API服务器: python api_server.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 检查服务器状态失败: {e}")
        sys.exit(1)
    
    print("✓ 服务器连接正常")
    
    # 运行测试
    results = []
    results.append(("提供商列表", test_tts_providers()))
    results.append(("音色列表", test_tts_voices()))
    results.append(("文本转语音", test_tts_synthesize()))
    results.append(("流式合成", test_tts_stream()))
    results.append(("多语言支持", test_tts_multilanguage()))
    results.append(("错误处理", test_tts_error_handling()))
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:20} {status}")
    
    print("-" * 60)
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        print("\n提示：")
        print("  - 运行 'python tests/test_tts_module_import.py' 测试模块导入")
        print("  - 运行 'python tests/test_tts_diagnosis.py' 进行完整诊断")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        print("\n建议：")
        print("  - 运行 'python tests/test_tts_diagnosis.py' 诊断问题")
        print("  - 检查日志文件: logs/api_server_*.log")
        return 1


if __name__ == "__main__":
    sys.exit(main())
