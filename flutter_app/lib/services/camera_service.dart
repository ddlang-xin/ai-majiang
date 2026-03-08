import 'dart:async';
import 'package:camera/camera.dart';
import 'package:permission_handler/permission_handler.dart';
import '../models/camera_enums.dart';

/// 摄像头管理服务
/// 提供摄像头初始化、图像流、拍照、切换摄像头等功能
class CameraService {
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  CameraStatus _status = CameraStatus.uninitialized;
  CameraPosition _currentPosition = CameraPosition.back;
  ResolutionPreset _currentResolution = ResolutionPreset.high;
  
  /// 图像流监听器
  StreamSubscription<CameraImage>? _imageStreamSubscription;
  
  /// 当前状态
  CameraStatus get status => _status;
  
  /// 当前摄像头位置
  CameraPosition get currentPosition => _currentPosition;
  
  /// 摄像头是否已初始化
  bool get isInitialized => _controller?.value.isInitialized ?? false;
  
  /// 获取可用摄像头列表
  Future<List<CameraDescription>> get availableCameras async {
    _cameras ??= await availableCameras();
    return _cameras!;
  }
  
  /// 检查并请求相机权限
  Future<bool> _checkPermission() async {
    final status = await Permission.camera.status;
    
    if (status.isGranted) {
      return true;
    }
    
    if (status.isDenied) {
      final result = await Permission.camera.request();
      return result.isGranted;
    }
    
    if (status.isPermanentlyDenied) {
      // 引导用户去设置页面开启权限
      await openAppSettings();
      return false;
    }
    
    return false;
  }
  
  /// 初始化摄像头
  /// [preset] 分辨率预设，默认 high
  Future<void> initialize({ResolutionPreset preset = ResolutionPreset.high}) async {
    if (_status == CameraStatus.ready || _status == CameraStatus.initializing) {
      return;
    }
    
    _status = CameraStatus.initializing;
    _currentResolution = preset;
    
    try {
      // 检查权限
      final hasPermission = await _checkPermission();
      if (!hasPermission) {
        _status = CameraStatus.error;
        throw Exception('相机权限未授权');
      }
      
      // 获取可用摄像头
      _cameras ??= await availableCameras();
      if (_cameras == null || _cameras!.isEmpty) {
        _status = CameraStatus.error;
        throw Exception('未检测到可用摄像头');
      }
      
      // 获取后置摄像头
      final camera = _cameras!.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => _cameras!.first,
      );
      
      _currentPosition = camera.lensDirection == CameraLensDirection.front
          ? CameraPosition.front
          : CameraPosition.back;
      
      // 创建控制器
      _controller = CameraController(
        camera,
        preset,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.yuv420,
      );
      
      // 初始化
      await _controller!.initialize();
      
      _status = CameraStatus.ready;
    } catch (e) {
      _status = CameraStatus.error;
      rethrow;
    }
  }
  
  /// 启动图像流
  /// [onImage] 图像帧回调，参数为 XFile 对象
  void startImageStream(Function(XFile image) onImage) {
    if (_controller == null || !_controller!.value.isInitialized) {
      throw Exception('摄像头未初始化');
    }
    
    if (_imageStreamSubscription != null) {
      return; // 已经启动了
    }
    
    _controller!.startImageStream((CameraImage image) {
      // 将 CameraImage 转换为 XFile (临时文件)
      // 这里简化处理，实际项目中可能需要转换格式
      // 注意：camera插件的imageStream返回的是CameraImage对象
      // 需要根据实际需求处理
    });
    
    // 实际实现：使用 takePicture 周期性捕获图像
    // 这里提供一种简化的实现方式
  }
  
  /// 简化版图像流：使用定时器模拟
  /// [onImage] 图像帧回调
  /// [intervalMs] 间隔时间（毫秒），默认 500ms
  Timer? _imageStreamTimer;
  
  void startImageStreamWithInterval(
    Function(XFile image) onImage, {
    int intervalMs = 500,
  }) {
    if (_controller == null || !_controller!.value.isInitialized) {
      throw Exception('摄像头未初始化');
    }
    
    stopImageStream();
    
    _imageStreamTimer = Timer.periodic(
      Duration(milliseconds: intervalMs),
      (timer) async {
        if (_controller != null && _controller!.value.isInitialized) {
          try {
            final file = await takePicture();
            onImage(file);
          } catch (e) {
            // 忽略单帧错误
          }
        }
      },
    );
  }
  
  /// 停止图像流
  void stopImageStream() {
    _imageStreamTimer?.cancel();
    _imageStreamTimer = null;
    
    try {
      if (_controller != null && _controller!.value.isInitialized) {
        _controller!.stopImageStream();
      }
    } catch (e) {
      // 忽略停止错误
    }
  }
  
  /// 拍照
  /// 返回 XFile 对象
  Future<XFile> takePicture() async {
    if (_controller == null || !_controller!.value.isInitialized) {
      throw Exception('摄像头未初始化');
    }
    
    if (_controller!.value.isTakingPicture) {
      throw Exception('正在拍照中');
    }
    
    return await _controller!.takePicture();
  }
  
  /// 切换摄像头
  Future<void> switchCamera() async {
    if (_cameras == null || _cameras!.length < 2) {
      throw Exception('无可用摄像头切换');
    }
    
    // 停止图像流
    stopImageStream();
    
    // 切换位置
    final newDirection = _currentPosition == CameraPosition.back
        ? CameraLensDirection.front
        : CameraLensDirection.back;
    
    // 查找对应摄像头
    final camera = _cameras!.firstWhere(
      (c) => c.lensDirection == newDirection,
      orElse: () => _cameras!.first,
    );
    
    // 释放旧控制器
    await _controller?.dispose();
    
    // 创建新控制器
    _controller = CameraController(
      camera,
      _currentResolution,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.yuv420,
    );
    
    await _controller!.initialize();
    
    _currentPosition = newDirection == CameraLensDirection.front
        ? CameraPosition.front
        : CameraPosition.back;
  }
  
  /// 释放资源
  Future<void> dispose() async {
    stopImageStream();
    await _controller?.dispose();
    _controller = null;
    _status = CameraStatus.disposed;
  }
  
  /// 获取当前控制器（用于预览）
  CameraController? get controller => _controller;
}
