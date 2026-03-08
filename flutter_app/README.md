# AI麻将助手 Flutter移动端

实时捕捉麻将画面并发送给AI分析的移动端应用。

## 功能特性

- 📷 实时摄像头预览
- 📸 点击拍摄捕获当前画面
- 🤖 发送图像给后端API分析
- 🎯 展示AI返回的推荐出牌

## 技术栈

- Flutter 3.x
- camera - 摄像头功能
- http - 网络请求
- permission_handler - 权限管理

## 项目结构

```
flutter_app/
├── lib/
│   └── main.dart          # 主程序代码
├── android/               # Android配置
├── ios/                   # iOS配置
└── pubspec.yaml          # 依赖配置
```

## 快速开始

### 1. 安装Flutter

确保已安装Flutter SDK，详见: https://flutter.dev/docs/get-started/install

### 2. 获取依赖

```bash
cd flutter_app
flutter pub get
```

### 3. 运行应用

```bash
flutter run
```

### 4. 构建APK

```bash
# Debug版本
flutter build apk --debug

# Release版本
flutter build apk --release
```

## API配置

在 `lib/main.dart` 中找到以下代码，修改后端API地址：

```dart
final response = await http.post(
  Uri.parse('http://localhost:8080/api/analyze'), // 修改为你的后端地址
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({'image': base64Image}),
);
```

## 权限说明

### Android

- `CAMERA` - 相机权限
- `INTERNET` - 网络权限

### iOS

- `NSCameraUsageDescription` - 相机使用说明

## 后端API要求

后端API需要实现以下接口：

### POST /api/analyze

**请求:**
```json
{
  "image": "base64编码的图像数据"
}
```

**响应:**
```json
{
  "recommendation": "推荐出牌: 🀇 一万\n原因：..."
}
```

## 演示模式

如果后端API不可用，应用会显示模拟的推荐结果，用于演示。

## 界面预览

1. **相机预览页**: 显示实时摄像头画面，中间有拍摄按钮
2. **结果页**: 显示拍摄的照片和AI推荐出牌结果

## 许可证

MIT License
