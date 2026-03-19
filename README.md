# 📚 智能读书 APP

一个免费的 Android 电子书朗读器，支持多种格式，中文 TTS 朗读。

## ✨ 功能特性

- 📖 **支持格式**: PDF, EPUB, AZW3, MOBI
- 🎙️ **中文 TTS**: 微软 Edge 免费语音（晓晓、云希等）
- ⚡ **语速调节**: 0.5x - 2.0x 可调
- ⏸️ **播放控制**: 播放/暂停/停止
- ⏱️ **定时关闭**: 15/30/45/60/90 分钟
- 📱 **章节导航**: 上一章/下一章
- 📊 **进度显示**: 实时阅读进度

## 🎯 声音选项

| 声音 | 性别 | 特点 |
|------|------|------|
| 晓晓 | 女声 | 温柔自然，最适合长时间收听 |
| 云希 | 男声 | 沉稳磁性 |
| 云扬 | 男声 | 清晰明亮 |
| 晓伊 | 女声 | 活泼轻快 |

## 📥 安装方法

### 方法一：直接安装 APK（推荐）

1. 在电脑上安装 WSL (Windows Subsystem for Linux)
2. 在 WSL 中运行打包命令
3. 将生成的 APK 传到手机安装

### 方法二：在 Linux/Mac 上打包

```bash
cd reader-app

# 安装 buildozer
pip install buildozer

# 初始化（首次运行）
buildozer init

# 打包成 APK
buildozer -v android debug

# 生成的 APK 在 bin/ 目录下
```

### 方法三：使用 Google Colab（无需本地环境）

我提供了一个 Colab 脚本，可以在云端打包：

```python
# 在 Google Colab 中运行
!pip install buildozer
!git clone https://github.com/yourusername/reader-app.git
%cd reader-app
!buildozer -v android debug
```

## 📱 手机安装

1. 将 APK 文件传到手机
2. 在手机设置中允许"未知来源"安装
3. 点击 APK 安装
4. 打开应用，选择书籍开始听书！

## 🔧 依赖说明

- **Kivy**: 跨平台 UI 框架
- **Edge TTS**: 微软免费中文语音合成
- **Pygame**: 音频播放
- **ebooklib/PyPDF2/mobi**: 电子书解析

## 💡 使用技巧

1. **首次使用**: 选择书籍后等待加载完成
2. **网络需求**: TTS 生成需要联网（Edge TTS 在线服务）
3. **离线使用**: 可以预先生成音频文件（后续版本支持）
4. **电池优化**: 长时间收听建议连接充电器

## 🚧 后续优化

- [ ] 支持声音克隆（录制你的声音）
- [ ] 离线 TTS 支持
- [ ] 书签功能
- [ ] 夜间模式
- [ ] 批量导入书籍

## 📄 许可证

MIT License - 完全免费，可自由修改分发

## 🙏 致谢

- Kivy 团队
- 微软 Edge TTS
- 所有开源电子书解析库

---

**开发时间**: 2026-03-15
**版本**: 1.0.0
